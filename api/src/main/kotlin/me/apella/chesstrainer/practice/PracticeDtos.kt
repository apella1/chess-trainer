package me.apella.chesstrainer.practice

import java.time.Instant
import java.util.UUID

data class DailyQueueResponse(
    val username: String,
    val puzzleIds: List<UUID>,
    val dueReviews: Int,
    val newPuzzles: Int,
)

data class RecordSessionRequest(
    val puzzlesTotal: Int,
    val puzzlesSolved: Int,
    val focusTypes: List<String> = emptyList(),
    val durationMs: Long? = null,
)

data class PracticeSessionDto(
    val id: UUID,
    val startedAt: Instant,
    val finishedAt: Instant?,
    val puzzlesTotal: Int,
    val puzzlesSolved: Int,
    val focusTypes: List<String>,
    val durationMs: Long?,
    val successRate: Double?,
)

fun PracticeSessionEntity.toDto() = PracticeSessionDto(
    id = id!!,
    startedAt = startedAt,
    finishedAt = finishedAt,
    puzzlesTotal = puzzlesTotal,
    puzzlesSolved = puzzlesSolved,
    focusTypes = focusTypes,
    durationMs = durationMs,
    successRate = if (puzzlesTotal > 0) {
        Math.round(puzzlesSolved * 100.0 / puzzlesTotal * 10) / 10.0
    } else null,
)
