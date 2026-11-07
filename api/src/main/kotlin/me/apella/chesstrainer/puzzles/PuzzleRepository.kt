package me.apella.chesstrainer.puzzles

import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.data.jpa.repository.Query
import org.springframework.data.repository.query.Param
import org.springframework.stereotype.Repository
import java.util.UUID

@Repository
interface PuzzleRepository : JpaRepository<PuzzleEntity, UUID> {

    /**
     * Find the next unsolved puzzle for a user.
     * Excludes puzzles the user has already attempted.
     */
    @Query(
        """
        SELECT p FROM PuzzleEntity p
        WHERE p.active = true
          AND (p.userId = :userId OR p.userId IS NULL)
          AND p.id NOT IN (
            SELECT a.puzzleId FROM PuzzleAttemptEntity a
            WHERE a.userId = :userId
          )
        ORDER BY p.createdAt DESC
        """,
    )
    fun findNextPuzzle(@Param("userId") userId: UUID): PuzzleEntity?
}

@Repository
interface PuzzleAttemptRepository : JpaRepository<PuzzleAttemptEntity, UUID> {

    fun countByPuzzleIdAndUserId(puzzleId: UUID, userId: UUID): Long
}
