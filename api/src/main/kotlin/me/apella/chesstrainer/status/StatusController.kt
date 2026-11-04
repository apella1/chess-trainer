package me.apella.chesstrainer.status

import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController

@RestController
@RequestMapping("/api/status")
class StatusController(private val statusService: StatusService) {

    @GetMapping
    fun getStatus(): ResponseEntity<StatusResponse> {
        return ResponseEntity.ok(statusService.getStatus())
    }
}
