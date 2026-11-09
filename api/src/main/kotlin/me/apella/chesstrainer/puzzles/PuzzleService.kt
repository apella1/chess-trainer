package me.apella.chesstrainer.puzzles

import me.apella.chesstrainer.common.NotFoundException
import me.apella.chesstrainer.practice.PracticeService
import me.apella.chesstrainer.users.UserService
import org.springframework.context.annotation.Lazy
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.util.UUID

/**
 * Business logic for puzzle retrieval and attempt recording.
 */
@Service
class PuzzleService(
    private val puzzleRepository: PuzzleRepository,
    private val attemptRepository: PuzzleAttemptRepository,
    private val userService: UserService,
    @Lazy private val practiceService: PracticeService,
) {

    /**
     * Get the next unsolved puzzle for a user.
     * Returns null if no more puzzles available.
     */
    fun getNextPuzzle(username: String, theme: String? = null): PuzzleDto? {
        val user = userService.findByUsername(username) ?: return null
        val pageable = org.springframework.data.domain.PageRequest.of(0, 1)
        return puzzleRepository.findNextPuzzle(user.id!!, theme, pageable).firstOrNull()?.toDto()
    }

    fun getThemes(username: String): List<String> {
        val user = userService.findByUsername(username) ?: return emptyList()
        return puzzleRepository.findThemesByUserId(user.id!!)
    }

    /**
     * Get the solution for a puzzle (for refutation display after solving).
     */
    fun getSolution(puzzleId: UUID): PuzzleSolutionDto {
        val puzzle = puzzleRepository.findById(puzzleId)
            .orElseThrow { NotFoundException("Puzzle $puzzleId not found") }
        return PuzzleSolutionDto(puzzleId, puzzle.solutionUci)
    }

    /**
     * Record a puzzle attempt. Idempotent per user — one attempt per puzzle per user.
     */
    @Transactional
    fun recordAttempt(puzzleId: UUID, username: String, request: AttemptRequest): AttemptResponse {
        val user = userService.findByUsername(username)
            ?: throw NotFoundException("User $username not found")

        val puzzle = puzzleRepository.findById(puzzleId)
            .orElseThrow { NotFoundException("Puzzle $puzzleId not found") }

        // Check if already attempted
        if (attemptRepository.countByPuzzleIdAndUserId(puzzleId, user.id!!) > 0) {
            throw IllegalStateException("Puzzle already attempted")
        }

        val attempt = PuzzleAttemptEntity(
            puzzleId = puzzleId,
            userId = user.id!!,
            solved = request.solved,
            movesTried = request.movesTried,
            timeMs = request.timeMs,
            hintsUsed = request.hintsUsed,
        )

        val saved = attemptRepository.save(attempt)

        // Update Leitner schedule
        practiceService.updateSchedule(puzzleId, user.id!!, request.solved)

        return saved.toResponse()
    }
}
