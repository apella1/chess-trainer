package me.apella.chesstrainer.puzzles

import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.GeneratedValue
import jakarta.persistence.GenerationType
import jakarta.persistence.Id
import jakarta.persistence.Table
import org.hibernate.annotations.JdbcTypeCode
import org.hibernate.type.SqlTypes
import java.time.Instant
import java.util.UUID

@Entity
@Table(name = "puzzles")
class PuzzleEntity(
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    val id: UUID? = null,

    @Column(name = "user_id")
    val userId: UUID? = null,

    @Column(nullable = false)
    val source: String = "own_game",

    @Column(name = "source_mistake_id")
    val sourceMistakeId: UUID? = null,

    @Column(nullable = false)
    val fen: String,

    @Column(name = "side_to_move", nullable = false)
    val sideToMove: String,

    @Column(name = "solution_uci", nullable = false, columnDefinition = "jsonb")
    @JdbcTypeCode(SqlTypes.JSON)
    val solutionUci: List<String> = emptyList(),

    @Column(nullable = false, columnDefinition = "jsonb")
    @JdbcTypeCode(SqlTypes.JSON)
    val themes: List<String> = emptyList(),

    @Column(name = "difficulty_est")
    val difficultyEst: Double? = null,

    @Column(nullable = false)
    var active: Boolean = true,

    @Column(name = "created_at", nullable = false)
    val createdAt: Instant = Instant.now(),
)

@Entity
@Table(name = "puzzle_attempts")
class PuzzleAttemptEntity(
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    val id: UUID? = null,

    @Column(name = "puzzle_id", nullable = false)
    val puzzleId: UUID,

    @Column(name = "user_id", nullable = false)
    val userId: UUID,

    @Column(nullable = false)
    val solved: Boolean,

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "moves_tried", columnDefinition = "jsonb")
    val movesTried: List<String> = emptyList(),

    @Column(name = "time_ms")
    val timeMs: Int? = null,

    @Column(name = "hints_used", nullable = false)
    val hintsUsed: Int = 0,

    @Column(name = "attempted_at", nullable = false)
    val attemptedAt: Instant = Instant.now(),
)
