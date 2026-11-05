package me.apella.chesstrainer.games

import me.apella.chesstrainer.common.NotFoundException
import me.apella.chesstrainer.common.PagedResponse
import me.apella.chesstrainer.common.PgnHeaders
import me.apella.chesstrainer.jobs.JobService
import me.apella.chesstrainer.users.UserService
import org.slf4j.LoggerFactory
import org.springframework.data.domain.PageRequest
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RequestParam
import org.springframework.web.bind.annotation.RestController
import org.springframework.web.multipart.MultipartFile
import java.time.Instant
import java.util.UUID

@RestController
@RequestMapping("/api/games")
class GamesController(
    private val gameRepository: GameRepository,
    private val userService: UserService,
    private val jobService: JobService,
) {

    private val log = LoggerFactory.getLogger(GamesController::class.java)

    /**
     * List games for a user with optional filters.
     *
     * Query params:
     *   - username (required): the chess.com username
     *   - result: win | loss | draw
     *   - color: white | black
     *   - timeClass: rapid | blitz | bullet | daily
     *   - page: zero-based page number (default 0)
     *   - size: page size (default 20)
     */
    @GetMapping
    fun listGames(
        @RequestParam username: String,
        @RequestParam(required = false) result: String?,
        @RequestParam(required = false) color: String?,
        @RequestParam(required = false) timeClass: String?,
        @RequestParam(defaultValue = "0") page: Int,
        @RequestParam(defaultValue = "20") size: Int,
    ): PagedResponse<GameSummaryDto> {
        // Find-only: do not create a user when just listing games
        val user = userService.findByUsername(username)
            ?: return PagedResponse.of(emptyList(), page, size, 0)
        val pageable = PageRequest.of(page, size)
        val gamesPage = gameRepository.findGames(user.id!!, result, color, timeClass, pageable)

        return PagedResponse.of(
            content = gamesPage.content.map { it.toSummary() },
            page = page,
            size = size,
            totalElements = gamesPage.totalElements,
        )
    }

    /**
     * Get a single game with full PGN for the game viewer.
     */
    @GetMapping("/{id}")
    fun getGame(@PathVariable id: UUID): GameDetailDto {
        val game = gameRepository.findById(id)
            .orElseThrow { NotFoundException("Game $id not found") }
        val moves = if (game.analysisStatus == "done") {
            gameRepository.findMovesWithEvals(id)
        } else {
            emptyList()
        }
        return game.toDetail(moves)
    }

    /**
     * Upload a PGN file (multipart/form-data).
     * A single file may contain multiple games.
     * Games are parsed, headers extracted, and inserted with source = 'pgn_upload'.
     *
     * Query params:
     *   - username (required): associates the uploaded games with a user
     */
    @PostMapping("/upload")
    fun uploadPgn(
        @RequestParam username: String,
        @RequestParam("file") file: MultipartFile,
    ): ResponseEntity<GameUploadResponse> {
        val user = userService.findOrCreateByUsername(username)
        val pgnText = String(file.bytes, Charsets.UTF_8)
        val gamePgns = PgnHeaders.splitGames(pgnText)

        var imported = 0
        var skipped = 0

        for (gamePgn in gamePgns) {
            val headers = PgnHeaders.parse(gamePgn)

            // Generate a pseudo-external ID from PGN headers
            // Format: white-black-date-result (lowercased)
            val white = headers["White"] ?: "unknown"
            val black = headers["Black"] ?: "unknown"
            val date = headers["Date"] ?: "unknown"
            val result = headers["Result"] ?: "*"
            val externalId = "pgn:${white.lowercase()}-${black.lowercase()}-$date-${result.replace("/", "")}"

            if (gameRepository.existsByUserIdAndSourceAndExternalId(user.id!!, "pgn_upload", externalId)) {
                skipped++
                continue
            }

            // Determine user color and result from headers
            val (userColor, userResult) = deriveColorAndResult(headers, username)

            val game = GameEntity(
                userId = user.id!!,
                source = "pgn_upload",
                externalId = externalId,
                url = headers["Link"],
                pgn = gamePgn,
                playedAt = parsePgnDate(headers),
                timeClass = null,
                timeControl = headers["TimeControl"],
                userColor = userColor,
                result = userResult,
                termination = headers["Termination"],
                userRating = parseRating(headers, userColor),
                oppRating = parseOppRating(headers, userColor),
                oppUsername = if (userColor == "white") headers["Black"] else headers["White"],
                eco = headers["ECO"],
                openingName = PgnHeaders.openingName(headers),
            )

            gameRepository.save(game)
            imported++
            // Enqueue analysis job for the uploaded game
            game.id?.let { jobService.enqueueAnalysis(user.id!!, it) }
        }

        log.info("PGN upload for {}: imported={}, skipped={}", username, imported, skipped)
        return ResponseEntity.ok(GameUploadResponse(imported, skipped, "$imported game(s) imported, $skipped skipped"))
    }

    /**
     * Determine the user's color and result from PGN headers.
     * Returns (color, result) where result is "win", "loss", or "draw".
     */
    private fun deriveColorAndResult(headers: Map<String, String>, username: String): Pair<String?, String?> {
        val white = headers["White"] ?: return Pair(null, null)
        val black = headers["Black"] ?: return Pair(null, null)
        val result = headers["Result"] ?: return Pair(null, null)

        val userColor = when {
            white.equals(username, ignoreCase = true) -> "white"
            black.equals(username, ignoreCase = true) -> "black"
            else -> null
        }

        if (userColor == null) return Pair(null, null)

        val userResult = when (result) {
            "1-0" -> if (userColor == "white") "win" else "loss"
            "0-1" -> if (userColor == "black") "win" else "loss"
            "1/2-1/2" -> "draw"
            else -> null
        }

        return Pair(userColor, userResult)
    }

    private fun parsePgnDate(headers: Map<String, String>): Instant? {
        val dateStr = headers["UTCDate"] ?: headers["Date"] ?: return null
        val timeStr = headers["UTCTime"] ?: "00:00:00"
        return try {
            Instant.parse("${dateStr.replace(".", "-")}T${timeStr}Z")
        } catch (e: Exception) {
            null
        }
    }

    private fun parseRating(headers: Map<String, String>, userColor: String?): Int? {
        if (userColor == null) return null
        val key = if (userColor == "white") "WhiteElo" else "BlackElo"
        return headers[key]?.toIntOrNull()
    }

    private fun parseOppRating(headers: Map<String, String>, userColor: String?): Int? {
        if (userColor == null) return null
        val key = if (userColor == "white") "BlackElo" else "WhiteElo"
        return headers[key]?.toIntOrNull()
    }
}
