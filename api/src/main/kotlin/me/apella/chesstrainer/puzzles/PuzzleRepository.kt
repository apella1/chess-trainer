package me.apella.chesstrainer.puzzles

import org.springframework.data.domain.Pageable
import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.data.jpa.repository.Query
import org.springframework.data.repository.query.Param
import org.springframework.stereotype.Repository
import java.util.UUID

@Repository
interface PuzzleRepository : JpaRepository<PuzzleEntity, UUID> {
    /**
     * Distinct themes across all active puzzles for a user.
     * Uses a native query to unnest the JSONB array.
     */
    @Query(
        value = """
            SELECT DISTINCT jsonb_array_elements_text(themes) as theme
            FROM puzzles
            WHERE active = true AND (user_id = :userId OR user_id IS NULL)
            ORDER BY theme
        """,
        nativeQuery = true,
    )
    fun findThemesByUserId(
        @Param("userId") userId: UUID,
    ): List<String>

    /**
     * Find the next unsolved puzzle for a user, optionally filtered by theme.
     * Excludes puzzles the user has already attempted.
     */
    @Query(
        value = """
            SELECT * FROM puzzles p
            WHERE p.active = true
              AND (p.user_id = :userId OR p.user_id IS NULL)
              AND (:theme IS NULL OR p.themes @> CAST(CONCAT('["', :theme, '"]') AS jsonb))
              AND p.id NOT IN (
                SELECT a.puzzle_id FROM puzzle_attempts a WHERE a.user_id = :userId
              )
            ORDER BY p.created_at DESC
        """,
        nativeQuery = true,
    )
    fun findNextPuzzle(
        @Param("userId") userId: UUID,
        @Param("theme") theme: String?,
        pageable: Pageable,
    ): List<PuzzleEntity>
}

@Repository
interface PuzzleAttemptRepository : JpaRepository<PuzzleAttemptEntity, UUID> {
    fun countByPuzzleIdAndUserId(
        puzzleId: UUID,
        userId: UUID,
    ): Long
}
