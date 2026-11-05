package me.apella.chesstrainer.games

import me.apella.chesstrainer.common.NotFoundException
import me.apella.chesstrainer.common.PgnHeaders
import me.apella.chesstrainer.jobs.JobService
import me.apella.chesstrainer.users.UserEntity
import me.apella.chesstrainer.users.UserService
import org.slf4j.LoggerFactory
import org.springframework.data.domain.PageRequest
import org.springframework.stereotype.Service
import java.time.Instant
import java.util.UUID

/**
 * Business logic for game operations: listing, detail retrieval, PGN upload.
 * Controllers delegate here; repositories are accessed only through this service.
 */
@Service
class GameService(
    private val gameRepository: GameRepository,
    private val userService: UserService,
    private val jobService: JobService,
) {

    private val log = LoggerFactory.getLogger(GameService::class.java)

    /**
     * List games for a user with optional filters. Returns empty if user not found.
     */
    fun listGames(
        username: String,
        result: String?,
        color: String?,
        timeClass: String?,
        page: Int,
        size: Int,
    ): List<GameSummaryDto> {
        val user = userService.findByUsername(username) ?: return emptyList()
        val pageable = PageRequest.of(page, size)
        return gameRepository.findGames(user.id!!, result, color, timeClass, pageable)
            .content.map { it.toSummary() }
    }

    fun countGames(username: String): Long {
        val user = userService.findByUsername(username) ?: return 0
        return gameRepository.countByUserId(user.id!!)
    }

    fun countGamesByUserId(userId: UUID): Long = gameRepository.countByUserId(userId)

    /**
     * Get a single game with PGN and move evaluations (if analyzed).
     */
    fun getGame(id: UUID): GameDetailDto {
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
     * Upload and import games from a PGN string. Multiple games per file are supported.
     * Idempotent on (userId, source, externalId). Enqueues analysis jobs for new games.
     */
    fun uploadPgn(username: String, pgnText: String): GameUploadResponse {
        val user = userService.findOrCreateByUsername(username)
        val gamePgns = PgnHeaders.splitGames(pgnText)

        var imported = 0
        var skipped = 0

        for (gamePgn in gamePgns) {
            val headers = PgnHeaders.parse(gamePgn)
            val externalId = buildExternalId(headers)

            if (gameRepository.existsByUserIdAndSourceAndExternalId(user.id!!, "pgn_upload", externalId)) {
                skipped++
                continue
            }

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
                userRating = extractRating(headers, userColor),
                oppRating = extractRating(headers, userColor, opponent = true),
                oppUsername = if (userColor == "white") headers["Black"] else headers["White"],
                eco = headers["ECO"],
                openingName = PgnHeaders.openingName(headers),
            )

            gameRepository.save(game)
            imported++
            game.id?.let { jobService.enqueueAnalysis(user.id!!, it) }
        }

        log.info("PGN upload for {}: imported={}, skipped={}", username, imported, skipped)
        return GameUploadResponse(imported, skipped, "$imported game(s) imported, $skipped skipped")
    }

    // --- Private helpers ---

    private fun buildExternalId(headers: Map<String, String>): String {
        val white = headers["White"] ?: "unknown"
        val black = headers["Black"] ?: "unknown"
        val date = headers["Date"] ?: "unknown"
        val result = headers["Result"] ?: "*"
        return "pgn:${white.lowercase()}-${black.lowercase()}-$date-${result.replace("/", "")}"
    }

    private fun deriveColorAndResult(headers: Map<String, String>, username: String): Pair<String?, String?> {
        val white = headers["White"] ?: return Pair(null, null)
        val black = headers["Black"] ?: return Pair(null, null)
        val result = headers["Result"] ?: return Pair(null, null)

        val userColor = when {
            white.equals(username, ignoreCase = true) -> "white"
            black.equals(username, ignoreCase = true) -> "black"
            else -> null
        } ?: return Pair(null, null)

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

    private fun extractRating(headers: Map<String, String>, userColor: String?, opponent: Boolean = false): Int? {
        if (userColor == null) return null
        val isWhite = (userColor == "white") xor opponent
        val key = if (isWhite) "WhiteElo" else "BlackElo"
        return headers[key]?.toIntOrNull()
    }
}
