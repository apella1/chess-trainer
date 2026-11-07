package me.apella.chesstrainer.reviews

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
@Table(name = "game_reviews")
class ReviewEntity(
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    val id: UUID? = null,

    @Column(name = "game_id", nullable = false)
    val gameId: UUID,

    @Column(name = "run_id")
    val runId: UUID? = null,

    @Column(nullable = false)
    val model: String,

    @Column(name = "prompt_version", nullable = false)
    val promptVersion: String = "v1",

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "facts_json", columnDefinition = "jsonb", nullable = false)
    val factsJson: Map<String, Any> = emptyMap(),

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "review_json", columnDefinition = "jsonb")
    val reviewJson: Map<String, Any>? = null,

    @Column(name = "review_text")
    val reviewText: String? = null,

    @Column(name = "validation_status", nullable = false)
    val validationStatus: String = "ok",

    @Column(name = "created_at", nullable = false)
    val createdAt: Instant = Instant.now(),
)
