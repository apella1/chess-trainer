package me.apella.chesstrainer.jobs

import org.slf4j.LoggerFactory
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.util.UUID

@Service
class JobService(private val jobRepository: JobRepository) {

    private val log = LoggerFactory.getLogger(JobService::class.java)

    /**
     * Enqueue an analyze_game job for a game if one doesn't already exist.
     * Idempotent: safe to call multiple times for the same game.
     */
    @Transactional
    fun enqueueAnalysis(userId: UUID, gameId: UUID) {
        if (jobRepository.existsByGameIdAndKind(gameId, "analyze_game")) {
            return
        }

        val job = JobEntity(
            userId = userId,
            gameId = gameId,
            kind = "analyze_game",
        )
        jobRepository.save(job)
        log.info("Enqueued analyze_game job for game {}", gameId)
    }
}
