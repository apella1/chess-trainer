package me.apella.chesstrainer.games

import me.apella.chesstrainer.common.PagedResponse
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RequestParam
import org.springframework.web.bind.annotation.RestController
import org.springframework.web.multipart.MultipartFile
import java.util.UUID

/**
 * Thin HTTP layer for game operations. All business logic is in GameService.
 */
@RestController
@RequestMapping("/api/games")
class GamesController(
    private val gameService: GameService,
) {
    @GetMapping
    fun listGames(
        @RequestParam username: String,
        @RequestParam(required = false) result: String?,
        @RequestParam(required = false) color: String?,
        @RequestParam(required = false) timeClass: String?,
        @RequestParam(defaultValue = "0") page: Int,
        @RequestParam(defaultValue = "20") size: Int,
    ): PagedResponse<GameSummaryDto> {
        val content = gameService.listGames(username, result, color, timeClass, page, size)
        val total = gameService.countGames(username)
        return PagedResponse.of(content, page, size, total)
    }

    @GetMapping("/{id}")
    fun getGame(
        @PathVariable id: UUID,
    ): GameDetailDto = gameService.getGame(id)

    @PostMapping("/upload")
    fun uploadPgn(
        @RequestParam username: String,
        @RequestParam("file") file: MultipartFile,
    ): ResponseEntity<GameUploadResponse> {
        val pgnText = String(file.bytes, Charsets.UTF_8)
        return ResponseEntity.ok(gameService.uploadPgn(username, pgnText))
    }
}
