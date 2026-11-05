package me.apella.chesstrainer.sync

import me.apella.chesstrainer.common.PgnHeaders
import me.apella.chesstrainer.games.GameEntity
import me.apella.chesstrainer.games.GameRepository
import me.apella.chesstrainer.users.UserEntity
import me.apella.chesstrainer.users.UserService
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Service
import java.time.Instant
import java.util.UUID
import java.util.concurrent.ConcurrentHashMap

@Service
class SyncService(
    private val chesscomClient: ChesscomClient,
    private val gameRepository: GameRepository,
    private val userService: UserService,
    private val syncedArchiveRepository: SyncedArchiveRepository,
) {

    private val log = LoggerFactory.getLogger(SyncService::class.java)
    private val syncProgressMap = ConcurrentHashMap<UUID, SyncProgress>()

    /**
     * Start a sync for a chess.com username.
     * Returns a sync progress ID immediately; the sync runs in a background thread.
     */
    fun startSync(username: String): SyncProgress {
        val progress = SyncProgress(username = username)
        syncProgressMap[progress.id] = progress

        val thread = Thread({
            runSync(progress, username)
        }, "sync-${progress.id}")
        thread.isDaemon = true
        thread.start()

        return progress
    }

    fun getProgress(syncId: UUID): SyncProgress? = syncProgressMap[syncId]

    private fun runSync(progress: SyncProgress, username: String) {
        try {
            log.info("Sync started for username={}", username)
            val user = userService.findOrCreateByUsername(username)

            // Fetch archive URLs (chess.com returns oldest-first)
            val allArchiveUrls = chesscomClient.fetchArchives(username)
            if (allArchiveUrls.isEmpty()) {
                progress.status = "done"
                progress.finishedAt = Instant.now()
                log.info("Sync complete: no archives found for {}", username)
                return
            }

            // Determine which archives to fetch using incremental sync:
            // 1. Skip archives already in synced_archives
            // 2. Always re-check the most recent synced archive (current month may have new games)
            val alreadySynced = syncedArchiveRepository.findArchiveUrlsByUserId(user.id!!).toSet()
            val mostRecentSynced = alreadySynced.maxByOrNull { it }

            val archivesToFetch = allArchiveUrls.filter { url ->
                url !in alreadySynced || url == mostRecentSynced
            }

            progress.archivesTotal = archivesToFetch.size
            log.info(
                "Sync for {}: {} total archives, {} already synced, {} to fetch",
                username, allArchiveUrls.size, alreadySynced.size, archivesToFetch.size,
            )

            if (archivesToFetch.isEmpty()) {
                progress.status = "done"
                progress.finishedAt = Instant.now()
                log.info("Sync complete: no new archives to fetch for {}", username)
                return
            }

            // Process most recent first for better UX
            for (archiveUrl in archivesToFetch.reversed()) {
                try {
                    val games = chesscomClient.fetchArchiveGames(archiveUrl)
                    progress.gamesFound += games.size

                    for (game in games) {
                        try {
                            val saved = importGame(user, game)
                            if (saved != null) {
                                progress.newGames++
                            }
                        } catch (e: Exception) {
                            log.warn("Error importing game: {}", e.message)
                        }
                    }

                    // Mark this archive as synced (idempotent — ON CONFLICT DO NOTHING
                    // would be ideal, but JpaRepository.save with IdClass handles this)
                    if (archiveUrl !in alreadySynced) {
                        syncedArchiveRepository.save(
                            SyncedArchive(userId = user.id!!, archiveUrl = archiveUrl)
                        )
                    }
                } catch (e: Exception) {
                    log.warn("Error processing archive {}: {}", archiveUrl, e.message)
                }

                progress.archivesProcessed++
            }

            progress.status = "done"
            progress.finishedAt = Instant.now()
            log.info(
                "Sync complete for {}: archives fetched={}/{}, gamesFound={}, newGames={}",
                username, progress.archivesProcessed, progress.archivesTotal,
                progress.gamesFound, progress.newGames,
            )
        } catch (e: Exception) {
            log.error("Sync failed for {}: {}", username, e.message, e)
            progress.status = "failed"
            progress.error = e.message
            progress.finishedAt = Instant.now()
        }
    }

    /**
     * Import a single chess.com game if it doesn't already exist.
     * Idempotent on (userId, source, externalId).
     */
    fun importGame(user: UserEntity, game: ChesscomGame): GameEntity? {
        val externalId = game.uuid
            ?: game.url?.substringAfterLast("/")
            ?: return null

        if (gameRepository.existsByUserIdAndSourceAndExternalId(user.id!!, "chesscom", externalId)) {
            return null
        }

        val pgn = game.pgn
        if (pgn.isBlank()) return null

        val headers = PgnHeaders.parse(pgn)
        val (userColor, userResult) = deriveColorAndResult(game, user.chesscomUsername)
        val playedAt = game.endTime?.let { Instant.ofEpochSecond(it) }

        val entity = GameEntity(
            userId = user.id!!,
            source = "chesscom",
            externalId = externalId,
            url = game.url,
            pgn = pgn,
            playedAt = playedAt,
            timeClass = game.timeClass,
            timeControl = game.timeControl,
            userColor = userColor,
            result = userResult,
            termination = headers["Termination"],
            userRating = if (userColor == "white") game.white.rating else game.black.rating,
            oppRating = if (userColor == "white") game.black.rating else game.white.rating,
            oppUsername = if (userColor == "white") game.black.username else game.white.username,
            eco = headers["ECO"],
            openingName = PgnHeaders.openingName(headers),
        )

        return gameRepository.save(entity)
    }

    /**
     * Determine the user's color and result from the chess.com game data.
     */
    private fun deriveColorAndResult(game: ChesscomGame, username: String): Pair<String?, String?> {
        val isWhite = game.white.username?.equals(username, ignoreCase = true) == true
        val isBlack = game.black.username?.equals(username, ignoreCase = true) == true

        val userColor = when {
            isWhite -> "white"
            isBlack -> "black"
            else -> return Pair(null, null)
        }

        val userSide = if (isWhite) game.white else game.black
        val oppSide = if (isWhite) game.black else game.white

        val userResult = when {
            userSide.result == "win" -> "win"
            oppSide.result == "win" -> "loss"
            userSide.result == "draw" || oppSide.result == "draw" -> "draw"
            listOf("stalemate", "insufficient", "repetition", "50move").any {
                userSide.result?.contains(it) == true || oppSide.result?.contains(it) == true
            } -> "draw"
            else -> null
        }

        return Pair(userColor, userResult)
    }
}
