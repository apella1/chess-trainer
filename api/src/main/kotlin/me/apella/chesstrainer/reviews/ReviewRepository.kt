package me.apella.chesstrainer.reviews

import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.stereotype.Repository
import java.util.UUID

@Repository
interface ReviewRepository : JpaRepository<ReviewEntity, UUID> {
    fun findFirstByGameIdOrderByCreatedAtDesc(gameId: UUID): ReviewEntity?
}
