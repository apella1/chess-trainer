package me.apella.chesstrainer.jobs

import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController

data class JobSummary(
    val pending: Int,
    val running: Int,
    val done: Int,
    val failed: Int,
    val byKind: Map<String, Map<String, Int>>,
)

data class JobSummaryResponse(
    val total: JobSummary,
)

@RestController
@RequestMapping("/api/jobs")
class JobsController(private val jobRepository: JobRepository) {

    /**
     * GET /api/jobs/summary — counts by status and kind.
     * The UI polls this to show job progress.
     */
    @GetMapping("/summary")
    fun getSummary(): JobSummaryResponse {
        val rows = jobRepository.countByStatusAndKind()

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
}
