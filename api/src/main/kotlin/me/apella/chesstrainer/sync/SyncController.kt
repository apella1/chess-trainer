package me.apella.chesstrainer.sync

import me.apella.chesstrainer.common.NotFoundException
import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController
import java.util.UUID

data class SyncRequest(val username: String)

data class SyncResponse(
    val syncId: UUID,
    val username: String,
    val status: String,
)

data class SyncProgressDto(
    val id: UUID,
    val username: String,
    val status: String,
    val archivesTotal: Int,
    val archivesProcessed: Int,
    val gamesFound: Int,
    val newGames: Int,
    val error: String?,
)

@RestController
@RequestMapping("/api/sync")
class SyncController(private val syncService: SyncService) {

    /**
     * Start a chess.com sync for the given username.
     * Returns 202 Accepted with a sync ID for polling progress.
     */
    @PostMapping
    fun startSync(@RequestBody request: SyncRequest): ResponseEntity<SyncResponse> {
        val progress = syncService.startSync(request.username)
        return ResponseEntity.accepted().body(
            SyncResponse(
                syncId = progress.id,
                username = progress.username,
                status = progress.status,
            )
        )
    }

    /**
     * Get the progress of a sync by its ID.
     */
    @GetMapping("/{id}")
    fun getProgress(@PathVariable id: UUID): SyncProgressDto {
        val progress = syncService.getProgress(id)
            ?: throw NotFoundException("Sync $id not found")
        return SyncProgressDto(
            id = progress.id,
            username = progress.username,
            status = progress.status,
            archivesTotal = progress.archivesTotal,
            archivesProcessed = progress.archivesProcessed,
            gamesFound = progress.gamesFound,
            newGames = progress.newGames,
            error = progress.error,
        )
    }
}
