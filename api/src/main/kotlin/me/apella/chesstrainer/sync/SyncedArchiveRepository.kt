package me.apella.chesstrainer.sync

import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.data.jpa.repository.Query
import org.springframework.stereotype.Repository
import java.util.UUID

@Repository
interface SyncedArchiveRepository : JpaRepository<SyncedArchive, SyncedArchiveId> {

    /**
     * Check if an archive URL has already been synced for a user.
     */
    fun existsByUserIdAndArchiveUrl(userId: UUID, archiveUrl: String): Boolean

    /**
     * Find all synced archive URLs for a user, ordered by URL (which is chronological
     * since chess.com URLs contain year/month).
     * Returns the URLs so the sync service can determine the most recent one.
     */
    @Query("SELECT sa.archiveUrl FROM SyncedArchive sa WHERE sa.userId = :userId ORDER BY sa.archiveUrl DESC")
    fun findArchiveUrlsByUserId(userId: UUID): List<String>

    /**
     * Delete all synced archive records for a user (used if a full re-sync is requested).
     */
    fun deleteByUserId(userId: UUID)
}
