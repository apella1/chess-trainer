package me.apella.chesstrainer.games

import java.time.Instant
import java.util.UUID

data class GameSummaryDto(
    val id: UUID,
    val playedAt: Instant?,
    val timeClass: String?,
    val timeControl: String?,
    val userColor: String?,
    val result: String?,
    val userRating: Int?,
    val oppRating: Int?,
    val oppUsername: String?,
    val eco: String?,
    val openingName: String?,
    val analysisStatus: String,
)

data class GameDetailDto(
    val id: UUID,
    val playedAt: Instant?,
    val timeClass: String?,
    val timeControl: String?,
    val userColor: String?,
    val result: String?,
    val termination: String?,
    val userRating: Int?,
    val oppRating: Int?,
    val oppUsername: String?,
    val eco: String?,
    val openingName: String?,
    val pgn: String,
    val analysisStatus: String,
)

data class GameUploadResponse(
    val imported: Int,
    val skipped: Int,
    val message: String,
)

fun GameEntity.toSummary() = GameSummaryDto(
    id = id!!,
    playedAt = playedAt,
    timeClass = timeClass,
    timeControl = timeControl,
    userColor = userColor,
    result = result,
    userRating = userRating,
    oppRating = oppRating,
    oppUsername = oppUsername,
    eco = eco,
    openingName = openingName,
    analysisStatus = analysisStatus,
)

fun GameEntity.toDetail() = GameDetailDto(
    id = id!!,
    playedAt = playedAt,
    timeClass = timeClass,
    timeControl = timeControl,
    userColor = userColor,
    result = result,
    termination = termination,
    userRating = userRating,
    oppRating = oppRating,
    oppUsername = oppUsername,
    eco = eco,
    openingName = openingName,
    pgn = pgn,
    analysisStatus = analysisStatus,
)
