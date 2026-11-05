package me.apella.chesstrainer.games

import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.GeneratedValue
import jakarta.persistence.GenerationType
import jakarta.persistence.Id
import jakarta.persistence.Table
import java.time.Instant
import java.util.UUID

@Entity
@Table(name = "games")
class GameEntity(
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    val id: UUID? = null,

    @Column(name = "user_id", nullable = false)
    val userId: UUID,

    @Column(nullable = false)
    val source: String = "chesscom",

    @Column(name = "external_id", nullable = false)
    val externalId: String,

    val url: String? = null,

    @Column(nullable = false)
    val pgn: String,

    @Column(name = "played_at")
    val playedAt: Instant? = null,

    @Column(name = "time_class")
    val timeClass: String? = null,

    @Column(name = "time_control")
    val timeControl: String? = null,

    @Column(name = "user_color")
    val userColor: String? = null,

    val result: String? = null,

    val termination: String? = null,

    @Column(name = "user_rating")
    val userRating: Int? = null,

    @Column(name = "opp_rating")
    val oppRating: Int? = null,

    @Column(name = "opp_username")
    val oppUsername: String? = null,

    val eco: String? = null,

    @Column(name = "opening_name")
    val openingName: String? = null,

    @Column(name = "analysis_status", nullable = false)
    var analysisStatus: String = "none",

    @Column(name = "created_at", nullable = false)
    val createdAt: Instant = Instant.now(),
)
