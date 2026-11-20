package me.apella.chesstrainer.users

import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.GeneratedValue
import jakarta.persistence.GenerationType
import jakarta.persistence.Id
import jakarta.persistence.Table
import java.time.Instant
import java.util.UUID

@Entity
@Table(name = "users")
class UserEntity(
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    val id: UUID? = null,
    @Column(name = "chesscom_username", unique = true, nullable = false)
    val chesscomUsername: String,
    @Column(name = "display_name", nullable = false)
    val displayName: String,
    @Column(name = "rating_band")
    var ratingBand: Int? = null,
    @Column(name = "created_at", nullable = false)
    val createdAt: Instant = Instant.now(),
)
