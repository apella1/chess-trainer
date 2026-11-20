package me.apella.chesstrainer.practice

import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.Id
import jakarta.persistence.IdClass
import jakarta.persistence.Table
import java.io.Serializable
import java.time.Instant
import java.util.UUID

data class ReviewScheduleId(
    val puzzleId: UUID = UUID(0, 0),
    val userId: UUID = UUID(0, 0),
) : Serializable

@Entity
@Table(name = "review_schedule")
@IdClass(ReviewScheduleId::class)
class ReviewScheduleEntity(
    @Id
    @Column(name = "puzzle_id")
    val puzzleId: UUID,
    @Id
    @Column(name = "user_id")
    val userId: UUID,
    /** Leitner box 1–5. Higher = less frequent review. */
    @Column(nullable = false)
    var box: Int = 1,
    /** Next time this puzzle should be presented. */
    @Column(name = "due_at", nullable = false)
    var dueAt: Instant = Instant.now(),
    /** Result of the last attempt (true = solved, false = failed, null = not attempted). */
    @Column(name = "last_result")
    var lastResult: Boolean? = null,
    /** Consecutive correct answers. */
    @Column(nullable = false)
    var streak: Int = 0,
)
