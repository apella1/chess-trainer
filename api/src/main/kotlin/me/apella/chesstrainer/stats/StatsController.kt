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
class StatsController(private val statsService: StatsService) {

    /**
     * GET /api/stats/weaknesses?username=...
     *
     * Returns ranked weaknesses by mistakes per 100 user moves.
     * Groups by mistake type across all analyzed games.
     */
    @GetMapping("/weaknesses")
    fun getWeaknesses(@RequestParam username: String): WeaknessesResponse {
        return statsService.getWeaknesses(username)
    }
}
