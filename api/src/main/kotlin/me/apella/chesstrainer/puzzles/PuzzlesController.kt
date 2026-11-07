package me.apella.chesstrainer.puzzles

import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RequestParam
import org.springframework.web.bind.annotation.RestController
import java.util.UUID

/**
 * Thin HTTP layer. All business logic is in PuzzleService.
 */
@RestController
@RequestMapping("/api/puzzles")
class PuzzlesController(private val puzzleService: PuzzleService) {

    /**
     * GET /api/puzzles/next?username=... — next unsolved puzzle for the user.
     */
    @GetMapping("/next")
    fun getNextPuzzle(
        @RequestParam username: String,
        @RequestParam(required = false) theme: String?,
    ): ResponseEntity<PuzzleDto> {
        val puzzle = puzzleService.getNextPuzzle(username, theme)
        return if (puzzle != null) ResponseEntity.ok(puzzle)
        else ResponseEntity.noContent().build()
    }

    @GetMapping("/themes")
    fun getThemes(@RequestParam username: String): List<String> {
        return puzzleService.getThemes(username)
    }

    /**
     * GET /api/puzzles/{id}/solution — full solution for refutation display.
     */
    @GetMapping("/{id}/solution")
    fun getSolution(@PathVariable id: UUID): PuzzleSolutionDto {
        return puzzleService.getSolution(id)
    }

    /**
     * POST /api/puzzles/{id}/attempts — record a solve attempt.
     */
    @PostMapping("/{id}/attempts")
    fun recordAttempt(
        @PathVariable id: UUID,
        @RequestParam username: String,
        @RequestBody request: AttemptRequest,
    ): AttemptResponse {
        return puzzleService.recordAttempt(id, username, request)
    }
}
