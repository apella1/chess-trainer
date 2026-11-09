package me.apella.chesstrainer.practice

import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RequestParam
import org.springframework.web.bind.annotation.RestController

/**
 * Thin HTTP layer. All business logic is in PracticeService.
 */
@RestController
@RequestMapping("/api/sessions")
class PracticeController(private val practiceService: PracticeService) {

    /**
     * GET /api/sessions/today?username=...
     * Returns today's practice queue: due reviews + new puzzles up to SESSION_SIZE.
     */
    @GetMapping("/today")
    fun getTodayQueue(@RequestParam username: String): DailyQueueResponse {
        return practiceService.getTodayQueue(username)
    }

    /**
     * POST /api/sessions?username=...
     * Record a completed practice session.
     */
    @PostMapping
    fun recordSession(
        @RequestParam username: String,
        @RequestBody request: RecordSessionRequest,
    ): ResponseEntity<PracticeSessionDto> {
        val session = practiceService.recordSession(username, request)
        return ResponseEntity.status(HttpStatus.CREATED).body(session)
    }

    /**
     * GET /api/sessions?username=...
     * Recent session history (last 14 days).
     */
    @GetMapping
    fun getRecentSessions(
        @RequestParam username: String,
        @RequestParam(defaultValue = "14") days: Int,
    ): List<PracticeSessionDto> {
        return practiceService.getRecentSessions(username, days)
    }
}
