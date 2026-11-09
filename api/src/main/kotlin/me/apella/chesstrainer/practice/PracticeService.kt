package me.apella.chesstrainer.practice

import me.apella.chesstrainer.puzzles.PuzzleAttemptRepository
import me.apella.chesstrainer.puzzles.PuzzleRepository
import me.apella.chesstrainer.users.UserService
import org.springframework.data.domain.PageRequest
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.time.Duration
import java.time.Instant
import java.util.UUID

/**
 * Leitner box durations (days between reviews per box level).
 * Box 1 = same day, Box 2 = 1 day, ..., Box 5 = 16 days.
 * Failed puzzles return to Box 1.
 */
private val BOX_INTERVALS_HOURS = mapOf(
    1 to 0L,
    2 to 24L,
    3 to 72L,
    4 to 192L,
    5 to 384L,
)

/** Target session size (number of puzzles). */
private const val SESSION_SIZE = 10

@Service
class PracticeService(
    private val reviewScheduleRepository: ReviewScheduleRepository,
    private val sessionRepository: PracticeSessionRepository,
    private val puzzleRepository: PuzzleRepository,
    private val attemptRepository: PuzzleAttemptRepository,
    private val userService: UserService,
) {

    /**
     * Get today's practice queue for a user.
     *
     * Combines:
     * 1. Due review_schedule entries (spaced repetition)
     * 2. New unseen puzzles to fill up to SESSION_SIZE
     *
     * Returns puzzle IDs in priority order.
     */
    fun getTodayQueue(username: String): DailyQueueResponse {
        val user = userService.findByUsername(username)
            ?: return DailyQueueResponse(username, emptyList(), 0, 0)

        val userId = user.id!!

        // Due reviews
        val dueReviews = reviewScheduleRepository.findDue(userId, SESSION_SIZE)
        val duePuzzleIds = dueReviews.map { it.puzzleId }

        // Fill remaining slots with new puzzles (not in schedule yet)
        val remaining = SESSION_SIZE - dueReviews.size
        val newPuzzles = if (remaining > 0) {
            puzzleRepository.findNextPuzzle(userId, null, PageRequest.of(0, remaining))
                .filter { it.id !in duePuzzleIds }
                .take(remaining)
        } else {
            emptyList()
        }

        val allPuzzleIds = duePuzzleIds + newPuzzles.mapNotNull { it.id }

        // Initialize schedule entries for new puzzles
        for (puzzle in newPuzzles) {
            val puzzleId = puzzle.id ?: continue
            if (reviewScheduleRepository.findByPuzzleIdAndUserId(puzzleId, userId) == null) {
                reviewScheduleRepository.save(
                    ReviewScheduleEntity(puzzleId = puzzleId, userId = userId)
                )
            }
        }

        return DailyQueueResponse(
            username = username,
            puzzleIds = allPuzzleIds,
            dueReviews = dueReviews.size,
            newPuzzles = newPuzzles.size,
        )
    }

    /**
     * Update the Leitner schedule after a puzzle attempt.
     * Called from the puzzle attempts flow when a user solves/fails.
     *
     * Solved: advance box (up to 5), set next due date per interval.
     * Failed: reset to box 1, due immediately.
     */
    @Transactional
    fun updateSchedule(puzzleId: UUID, userId: UUID, solved: Boolean) {
        val schedule = reviewScheduleRepository.findByPuzzleIdAndUserId(puzzleId, userId)
            ?: ReviewScheduleEntity(puzzleId = puzzleId, userId = userId)

        if (solved) {
            schedule.box = minOf(schedule.box + 1, 5)
            schedule.streak += 1
        } else {
            schedule.box = 1
            schedule.streak = 0
        }

        schedule.lastResult = solved
        val intervalHours = BOX_INTERVALS_HOURS[schedule.box] ?: 0L
        schedule.dueAt = Instant.now().plus(Duration.ofHours(intervalHours))

        reviewScheduleRepository.save(schedule)
    }

    /**
     * Record a completed practice session.
     */
    @Transactional
    fun recordSession(username: String, request: RecordSessionRequest): PracticeSessionDto {
        val user = userService.findByUsername(username)
            ?: throw IllegalArgumentException("User $username not found")

        val session = PracticeSessionEntity(
            userId = user.id!!,
            finishedAt = Instant.now(),
            puzzlesTotal = request.puzzlesTotal,
            puzzlesSolved = request.puzzlesSolved,
            focusTypes = request.focusTypes,
            durationMs = request.durationMs,
        )

        return sessionRepository.save(session).toDto()
    }

    /**
     * Get recent session history for a user.
     */
    fun getRecentSessions(username: String, days: Int = 14): List<PracticeSessionDto> {
        val user = userService.findByUsername(username) ?: return emptyList()
        val since = Instant.now().minus(Duration.ofDays(days.toLong()))
        return sessionRepository.findByUserIdSince(user.id!!, since).map { it.toDto() }
    }
}
