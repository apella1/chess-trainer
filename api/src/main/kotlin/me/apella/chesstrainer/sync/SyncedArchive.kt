package me.apella.chesstrainer.sync

import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.Id
import jakarta.persistence.IdClass
import jakarta.persistence.Table
import java.io.Serializable
import java.time.Instant
import java.util.UUID

data class SyncedArchiveId(
    val userId: UUID = UUID(0, 0),
    val archiveUrl: String = "",
) : Serializable

@Entity
@Table(name = "synced_archives")
@IdClass(SyncedArchiveId::class)
class SyncedArchive(
    @Id
    @Column(name = "user_id")
    val userId: UUID,

    @Id
    @Column(name = "archive_url")
    val archiveUrl: String,

    @Column(name = "synced_at")
    val syncedAt: Instant = Instant.now(),
)
