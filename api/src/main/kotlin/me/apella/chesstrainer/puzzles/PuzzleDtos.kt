package me.apella.chesstrainer.puzzles

import java.time.Instant
import java.util.UUID

data class PuzzleDto(
    val id: UUID,
    val fen: String,
    val sideToMove: String,
    val solutionLength: Int,
    val themes: List<String>,
    val source: String,
)

data class AttemptRequest(
    val solved: Boolean,
    val movesTried: List<String> = emptyList(),
    val timeMs: Int? = null,
    val hintsUsed: Int = 0,
)

data class AttemptResponse(
    val id: UUID,
    val puzzleId: UUID,
    val solved: Boolean,
    val attemptedAt: Instant,
)

data class PuzzleSolutionDto(
    val puzzleId: UUID,
    val solutionUci: List<String>,
)

fun PuzzleEntity.toDto() = PuzzleDto(
    id = id!!,
    fen = fen,
    sideToMove = sideToMove,
    solutionLength = solutionUci.size,
    themes = themes,
    source = source,
)

fun PuzzleAttemptEntity.toResponse() = AttemptResponse(
    id = id!!,
    puzzleId = puzzleId,
    solved = solved,
    attemptedAt = attemptedAt,
)
