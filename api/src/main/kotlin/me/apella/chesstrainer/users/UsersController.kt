package me.apella.chesstrainer.users

import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController

data class UserSummary(
    val username: String,
    val displayName: String,
    val gameCount: Long,
)

@RestController
@RequestMapping("/api/users")
class UsersController(
    private val userRepository: UserRepository,
    private val gameRepository: me.apella.chesstrainer.games.GameRepository,
) {

    /**
 s     * GET /api/users — list all synced users with their game counts.
     * Used by the Games page dropdown to avoid retyping usernames.
     */
    @GetMapping
    fun listUsers(): List<UserSummary> {
        return userRepository.findAll()
            .map { user ->
                UserSummary(
                    username = user.chesscomUsername,
                    displayName = user.displayName,
                    gameCount = gameRepository.countByUserId(user.id!!),
                )
            }
            .filter { it.gameCount > 0 }  // only show users with synced games
            .sortedByDescending { it.gameCount }
    }
}
