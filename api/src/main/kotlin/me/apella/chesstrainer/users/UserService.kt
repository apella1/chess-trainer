package me.apella.chesstrainer.users

import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.util.UUID

@Service
class UserService(private val userRepository: UserRepository) {

    fun findById(id: UUID): UserEntity =
        userRepository.findById(id).orElseThrow { IllegalArgumentException("User $id not found") }

    /**
     * Find or create a user by their chess.com username.
     * On first sync, a new user row is created with the username as display name.
     */
    @Transactional
    fun findOrCreateByUsername(chesscomUsername: String): UserEntity {
        return userRepository.findByChesscomUsername(chesscomUsername)
            .orElseGet {
                val user = UserEntity(
                    chesscomUsername = chesscomUsername,
                    displayName = chesscomUsername,
                )
                userRepository.save(user)
            }
    }
}
