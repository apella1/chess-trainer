package me.apella.chesstrainer.practice

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
@Table(name = "practice_sessions")
class PracticeSessionEntity(
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    val id: UUID? = null,
    @Column(name = "user_id", nullable = false)
    val userId: UUID,
    @Column(name = "started_at", nullable = false)
    val startedAt: Instant = Instant.now(),
    @Column(name = "finished_at")
    var finishedAt: Instant? = null,
    @Column(name = "puzzles_total", nullable = false)
    var puzzlesTotal: Int = 0,
    @Column(name = "puzzles_solved", nullable = false)
    var puzzlesSolved: Int = 0,
    @Column(name = "focus_types", nullable = false, columnDefinition = "jsonb")
    @JdbcTypeCode(SqlTypes.JSON)
    var focusTypes: List<String> = emptyList(),
    @Column(name = "duration_ms")
    var durationMs: Long? = null,
)
