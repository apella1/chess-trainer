package me.apella.chesstrainer.sync

import java.time.Instant
import java.util.UUID

/**
 * In-memory sync progress tracking.
 * Phase 1 uses a ConcurrentHashMap; this is intentionally not persisted.
 * If the API restarts mid-sync, the user re-triggers and idempotency handles duplicates.
 */
data class SyncProgress(
    val id: UUID = UUID.randomUUID(),
    val username: String,
    var status: String = "running", // running | done | failed
    var archivesTotal: Int = 0,
    var archivesProcessed: Int = 0,
    var gamesFound: Int = 0,
    var newGames: Int = 0,
    var error: String? = null,
    val startedAt: Instant = Instant.now(),
    var finishedAt: Instant? = null,
)
