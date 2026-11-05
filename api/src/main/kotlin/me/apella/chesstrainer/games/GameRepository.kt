package me.apella.chesstrainer.games

import org.springframework.data.domain.Page
import org.springframework.data.domain.Pageable
import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.data.jpa.repository.Query
import org.springframework.data.repository.query.Param
import org.springframework.stereotype.Repository
import java.util.UUID

@Repository
interface GameRepository : JpaRepository<GameEntity, UUID> {

    /**
     * List games for a user with optional filters.
     * Null filters are ignored (not applied).
     */
    @Query(
        """
        SELECT g FROM GameEntity g
        WHERE g.userId = :userId
          AND (:result IS NULL OR g.result = :result)
          AND (:userColor IS NULL OR g.userColor = :userColor)
          AND (:timeClass IS NULL OR g.timeClass = :timeClass)
        ORDER BY g.playedAt DESC
        """,
    )
    fun findGames(
        @Param("userId") userId: UUID,
        @Param("result") result: String?,
        @Param("userColor") userColor: String?,
        @Param("timeClass") timeClass: String?,
        pageable: Pageable,
    ): Page<GameEntity>

    /**
     * Check if a game already exists by external ID.
     * Used for idempotency during sync.
     */
    fun existsByUserIdAndSourceAndExternalId(
        userId: UUID,
        source: String,
        externalId: String,
    ): Boolean

    /**
     * Count games for a user.
     */
    fun countByUserId(userId: UUID): Long
}
