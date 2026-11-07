package me.apella.chesstrainer.jobs

import org.slf4j.LoggerFactory
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.util.UUID

@Service
class JobService(private val jobRepository: JobRepository) {

    private val log = LoggerFactory.getLogger(JobService::class.java)

    /**
     * Get a job summary: counts by status and kind.
     */
    fun getSummary(): JobSummaryResponse {
        val rows = jobRepository.getSummary()

        var pending = 0
        var running = 0
        var done = 0
        var failed = 0
        val byKind = mutableMapOf<String, MutableMap<String, Int>>()

        for (row in rows) {
            val status = row[0] as String
            val kind = row[1] as String
            val count = (row[2] as Number).toInt()

            when (status) {
                "pending" -> pending += count
                "running" -> running += count
                "done" -> done += count
                "failed" -> failed += count
            }
            byKind.getOrPut(kind) { mutableMapOf() }[status] = count
        }

        return JobSummaryResponse(
            total = JobSummary(
                pending = pending,
                running = running,
                done = done,
                failed = failed,
                byKind = byKind.mapValues { it.value.toMap() },
            ),
        )
    }

    /**
     * Enqueue an analyze_game job for a game if one doesn't already exist.
     * Idempotent: safe to call multiple times for the same game.
     */
    @Transactional
    fun enqueueAnalysis(userId: UUID, gameId: UUID) {
        if (jobRepository.existsByGameIdAndKind(gameId, "analyze_game")) {
            return
        }
        val job = JobEntity(userId = userId, gameId = gameId, kind = "analyze_game")
        jobRepository.save(job)
        log.info("Enqueued analyze_game job for game {}", gameId)
    }

    /**
     * Enqueue a review_game job. Multiple review jobs are allowed (for regeneration);
     * the worker skips if a review already exists for the current model+version.
     */
    @Transactional
    fun enqueueReview(userId: UUID, gameId: UUID) {
        val job = JobEntity(userId = userId, gameId = gameId, kind = "review_game")
        jobRepository.save(job)
        log.info("Enqueued review_game job for game {}", gameId)
    }
}
