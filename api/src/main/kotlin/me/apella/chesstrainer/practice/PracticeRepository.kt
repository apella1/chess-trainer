package me.apella.chesstrainer.practice

import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.data.jpa.repository.Query
import org.springframework.data.repository.query.Param
import org.springframework.stereotype.Repository
import java.time.Instant
import java.util.UUID

@Repository
interface ReviewScheduleRepository : JpaRepository<ReviewScheduleEntity, ReviewScheduleId> {
    /**
     * Puzzles due for review now, ordered by box ascending (lowest box = most urgent).
     * Capped at limit.
     */
    @Query(
        value = """
            SELECT * FROM review_schedule
            WHERE user_id = :userId AND due_at <= now()
            ORDER BY box ASC, due_at ASC
            LIMIT :limit
        """,
        nativeQuery = true,
    )
    fun findDue(
        @Param("userId") userId: UUID,
        @Param("limit") limit: Int,
    ): List<ReviewScheduleEntity>

    fun findByPuzzleIdAndUserId(
        puzzleId: UUID,
        userId: UUID,
    ): ReviewScheduleEntity?
}

@Repository
interface PracticeSessionRepository : JpaRepository<PracticeSessionEntity, UUID> {
    fun findFirstByUserIdOrderByStartedAtDesc(userId: UUID): PracticeSessionEntity?

    @Query(
        "SELECT s FROM PracticeSessionEntity s WHERE s.userId = :userId AND s.startedAt >= :since ORDER BY s.startedAt DESC",
    )
    fun findByUserIdSince(
        @Param("userId") userId: UUID,
        @Param("since") since: Instant,
    ): List<PracticeSessionEntity>
}
