package me.apella.chesstrainer.stats

import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RequestParam
import org.springframework.web.bind.annotation.RestController

/**
 * Thin HTTP layer. All business logic is in StatsService.
 */
@RestController
@RequestMapping("/api/stats")
class StatsController(
    private val statsService: StatsService,
) {
    /**
     * GET /api/stats/weaknesses?username=...&phase=...
     *
     * Returns ranked weaknesses by mistakes per 100 user moves.
     * Groups by mistake type across all analyzed games, with optional phase filter.
     */
    @GetMapping("/weaknesses")
    fun getWeaknesses(
        @RequestParam username: String,
        @RequestParam(required = false) phase: String?,
    ): WeaknessesResponse = statsService.getWeaknesses(username, phase)

    /**
     * GET /api/stats/trends?username=...&periods=6
     * Mistake rates by type per month over the last N periods.
     */
    @GetMapping("/trends")
    fun getTrends(
        @RequestParam username: String,
        @RequestParam(defaultValue = "6") periods: Int,
    ): TrendsResponse = statsService.getTrends(username, periods)
}
