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

/**
 * Thin HTTP layer. All business logic is in JobService.
 */
@RestController
@RequestMapping("/api/jobs")
class JobsController(
    private val jobService: JobService,
) {
    /**
     * GET /api/jobs/summary — counts by status and kind.
     */
    @GetMapping("/summary")
    fun getSummary(): JobSummaryResponse = jobService.getSummary()
}
