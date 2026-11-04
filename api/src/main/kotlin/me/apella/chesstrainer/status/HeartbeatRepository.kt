package me.apella.chesstrainer.status

import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.Id
import jakarta.persistence.IdClass
import jakarta.persistence.Table
import org.hibernate.annotations.JdbcTypeCode
import org.hibernate.type.SqlTypes
import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.data.jpa.repository.Query
import org.springframework.stereotype.Repository
import java.io.Serializable
import java.time.Instant

// Composite PK class
data class HeartbeatId(
    val service: String = "",
    val instance: String = "",
) : Serializable

@Entity
@Table(name = "service_heartbeats")
@IdClass(HeartbeatId::class)
class ServiceHeartbeat(
    @Id
    val service: String,

    @Id
    val instance: String,

    @Column(name = "last_seen")
    val lastSeen: Instant = Instant.now(),

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    val details: Map<String, Any> = emptyMap(),
)

@Repository
interface HeartbeatRepository : JpaRepository<ServiceHeartbeat, HeartbeatId> {

    @Query(
        """
        SELECT h FROM ServiceHeartbeat h
        WHERE h.service = :service
        ORDER BY h.lastSeen DESC
        LIMIT 1
        """,
        nativeQuery = false,
    )
    fun findLatestForService(service: String): ServiceHeartbeat?
}
