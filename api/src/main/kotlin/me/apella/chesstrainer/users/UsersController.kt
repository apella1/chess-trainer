package me.apella.chesstrainer.users

import me.apella.chesstrainer.games.GameService
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController

data class UserSummary(
    val username: String,
    val displayName: String,
    val gameCount: Long,
)

/**
 * Thin HTTP layer. Uses UserService and GameService — never touches repositories directly.
 */
@RestController
@RequestMapping("/api/users")
class UsersController(
    private val userService: UserService,
    private val gameService: GameService,
) {
    /**
     * GET /api/users — list all synced users with their game counts.
     * Only shows users who have at least one synced game.
     */
    @GetMapping
    fun listUsers(): List<UserSummary> =
        userService
            .findAll()
            .map { user ->
                UserSummary(
                    username = user.chesscomUsername,
                    displayName = user.displayName,
                    gameCount = gameService.countGamesByUserId(user.id!!),
                )
            }.filter { it.gameCount > 0 }
            .sortedByDescending { it.gameCount }
}
