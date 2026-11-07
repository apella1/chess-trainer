package me.apella.chesstrainer.reviews

import java.time.Instant
import java.util.UUID

data class ReviewDto(
    val id: UUID,
    val gameId: UUID,
    val model: String,
    val promptVersion: String,
    val reviewText: String?,
    val reviewJson: Map<String, Any>?,
    val validationStatus: String,
    val createdAt: Instant,
)

fun ReviewEntity.toDto() = ReviewDto(
    id = id!!,
    gameId = gameId,
    model = model,
    promptVersion = promptVersion,
    reviewText = reviewText,
    reviewJson = reviewJson,
    validationStatus = validationStatus,
    createdAt = createdAt,
)
