package me.apella.chesstrainer.jobs

import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.data.jpa.repository.Query
import org.springframework.stereotype.Repository
import java.util.UUID

@Repository
interface JobRepository : JpaRepository<JobEntity, UUID> {
    /**
     * Count jobs grouped by status and kind.
     * Returns rows of [status, kind, count].
     */
    @Query(
        """
        SELECT j.status, j.kind, COUNT(j)
        FROM JobEntity j
        GROUP BY j.status, j.kind
        """,
    )
    fun countByStatusAndKind(): List<Array<Any>>

    /**
     * Check if an analyze_game job already exists for a game.
     * Used by sync to avoid enqueuing duplicate jobs.
     */
    fun existsByGameIdAndKind(
        gameId: UUID,
        kind: String,
    ): Boolean

    /**
     * Get job counts grouped by status and kind.
     */
    fun getSummary(): List<Array<Any>> = countByStatusAndKind()
}
