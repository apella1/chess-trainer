package me.apella.chesstrainer.reviews

import me.apella.chesstrainer.common.NotFoundException
import me.apella.chesstrainer.games.GameRepository
import me.apella.chesstrainer.jobs.JobService
import org.springframework.stereotype.Service
import java.util.UUID

@Service
class ReviewService(
    private val reviewRepository: ReviewRepository,
    private val gameRepository: GameRepository,
    private val jobService: JobService,
) {
    /**
     * Get the latest review for a game. Returns null if none exists yet.
     */
    fun getLatestReview(gameId: UUID): ReviewDto? = reviewRepository.findFirstByGameIdOrderByCreatedAtDesc(gameId)?.toDto()

    /**
     * Enqueue a new review_game job for a game.
     * Idempotent: the worker checks for an existing review and skips if one exists.
     */
    fun enqueueReview(gameId: UUID): Boolean {
        val game =
            gameRepository
                .findById(gameId)
                .orElseThrow { NotFoundException("Game $gameId not found") }

        if (game.analysisStatus != "done") {
            throw IllegalStateException("Game $gameId has not been analyzed yet")
        }

        jobService.enqueueReview(game.userId, gameId)
        return true
    }
}
