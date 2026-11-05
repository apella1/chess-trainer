package me.apella.chesstrainer.jobs

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
@Table(name = "analysis_jobs")
class JobEntity(
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    val id: UUID? = null,

    @Column(name = "user_id", nullable = false)
    val userId: UUID,

    @Column(name = "game_id")
    val gameId: UUID? = null,

    @Column(nullable = false)
    val kind: String,

    @Column(nullable = false)
    var status: String = "pending",

    @Column(nullable = false)
    var attempts: Int = 0,

    @Column(name = "max_attempts", nullable = false)
    var maxAttempts: Int = 3,

    @Column(name = "locked_by")
    var lockedBy: String? = null,

    @Column(name = "locked_at")
    var lockedAt: Instant? = null,

    @Column(name = "last_error")
    var lastError: String? = null,

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    val payload: Map<String, Any> = emptyMap(),

    @Column(name = "created_at", nullable = false)
    val createdAt: Instant = Instant.now(),

    @Column(name = "started_at")
    var startedAt: Instant? = null,

    @Column(name = "finished_at")
    var finishedAt: Instant? = null,
)
