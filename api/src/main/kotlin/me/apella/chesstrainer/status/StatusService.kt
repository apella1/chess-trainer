package me.apella.chesstrainer.status

import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.stereotype.Service
import java.time.Duration
import java.time.Instant

data class WorkerStatus(
    val status: String,           // "ok" | "stale" | "down"
    val lastSeenSeconds: Long?,
    val details: Map<String, Any>,
)

data class StatusResponse(
    val api: String,
    val database: String,
    val worker: WorkerStatus,
    val ollama: String,
)

@Service
class StatusService(
    private val heartbeatRepository: HeartbeatRepository,
    private val jdbcTemplate: JdbcTemplate,
) {

    fun getStatus(): StatusResponse {
        val dbStatus = checkDatabase()
        val workerStatus = checkWorker()
        val ollamaStatus = deriveOllamaStatus(workerStatus)

        return StatusResponse(
            api = "ok",
            database = dbStatus,
            worker = workerStatus,
            ollama = ollamaStatus,
        )
    }

    private fun checkDatabase(): String {
        return try {
            jdbcTemplate.queryForObject("SELECT 1", Int::class.java)
            "ok"
        } catch (ex: Exception) {
            "down"
        }
    }

    private fun checkWorker(): WorkerStatus {
        val heartbeat = heartbeatRepository.findLatestForService("worker")
            ?: return WorkerStatus(status = "down", lastSeenSeconds = null, details = emptyMap())

        val age = Duration.between(heartbeat.lastSeen, Instant.now())
        val ageSeconds = age.seconds

        val status = when {
            ageSeconds <= 30 -> "ok"
            ageSeconds <= 300 -> "stale"
            else -> "down"
        }

        return WorkerStatus(
            status = status,
            lastSeenSeconds = ageSeconds,
            details = heartbeat.details,
        )
    }

    /**
     * Ollama reachability is reported by the worker in its heartbeat details.
     * If the worker is down, we cannot determine Ollama status.
     */
    private fun deriveOllamaStatus(worker: WorkerStatus): String {
        if (worker.status == "down") return "unknown"
        val reachable = worker.details["ollamaReachable"] as? Boolean ?: return "unknown"
        return if (reachable) "ok" else "down"
    }
}
