package me.apella.chesstrainer.reviews

import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController
import java.util.UUID

/**
 * Thin HTTP layer. All business logic is in ReviewService.
 */
@RestController
@RequestMapping("/api/games/{gameId}/review")
class ReviewsController(
    private val reviewService: ReviewService,
) {
    /**
     * GET /api/games/{gameId}/review — latest stored review.
     * Returns 204 if no review exists yet.
     */
    @GetMapping
    fun getReview(
        @PathVariable gameId: UUID,
    ): ResponseEntity<ReviewDto> {
        val review = reviewService.getLatestReview(gameId)
        return if (review != null) {
            ResponseEntity.ok(review)
        } else {
            ResponseEntity.noContent().build()
        }
    }

    /**
     * POST /api/games/{gameId}/review/regenerate — enqueue a new review job.
     * Returns 202 Accepted.
     */
    @PostMapping("/regenerate")
    fun regenerateReview(
        @PathVariable gameId: UUID,
    ): ResponseEntity<Map<String, String>> {
        reviewService.enqueueReview(gameId)
        return ResponseEntity
            .status(HttpStatus.ACCEPTED)
            .body(mapOf("message" to "Review generation queued for game $gameId"))
    }
}
