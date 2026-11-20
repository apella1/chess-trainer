package me.apella.chesstrainer.status

import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.stereotype.Service
import java.time.Duration
import java.time.Instant

data class WorkerStatus(
    val status: String, // "ok" | "stale" | "down"
    val lastSeenSeconds: Long?,
    val details: Map<String, Any>,
)

/**
 * Ollama has two independent health dimensions:
 * - reachable: the Ollama server process is running and responding
 * - modelReady: the configured model is fully downloaded and available
 *
 * A model still downloading will show reachable=true, modelReady=false.
 * This prevents confusing "Ollama is fine" when reviews would actually fail.
 */
data class OllamaStatus(
    val status: String, // "ok" | "down" | "model_not_ready" | "unknown"
    val model: String?,
    val detail: String?,
)

data class StatusResponse(
    val api: String,
    val database: String,
    val worker: WorkerStatus,
    val ollama: OllamaStatus,
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

    private fun checkDatabase(): String =
        try {
            jdbcTemplate.queryForObject("SELECT 1", Int::class.java)
            "ok"
        } catch (ex: Exception) {
            "down"
        }

    private fun checkWorker(): WorkerStatus {
        val heartbeat =
            heartbeatRepository.findLatestForService("worker")
                ?: return WorkerStatus(status = "down", lastSeenSeconds = null, details = emptyMap())

        val age = Duration.between(heartbeat.lastSeen, Instant.now())
        val ageSeconds = age.seconds

        val status =
            when {
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
     * Derives Ollama status from the worker's heartbeat details.
     *
     * Three possible states the worker reports:
     * - ollamaReachable=false                      → Ollama server is down
     * - ollamaReachable=true, modelReady=false      → Server up, model still downloading
     * - ollamaReachable=true, modelReady=true       → Fully ready
     *
     * If the worker is down we cannot determine Ollama status at all.
     */
    private fun deriveOllamaStatus(worker: WorkerStatus): OllamaStatus {
        if (worker.status == "down") {
            return OllamaStatus(status = "unknown", model = null, detail = "Worker is down; cannot determine Ollama status")
        }

        val reachable =
            worker.details["ollamaReachable"] as? Boolean
                ?: return OllamaStatus(status = "unknown", model = null, detail = "No Ollama data in heartbeat")

        val model = worker.details["ollamaModel"] as? String

        if (!reachable) {
            return OllamaStatus(
                status = "down",
                model = model,
                detail = "Ollama server is not reachable at the configured URL",
            )
        }

        val modelReady = worker.details["ollamaModelReady"] as? Boolean ?: false
        return if (modelReady) {
            OllamaStatus(status = "ok", model = model, detail = null)
        } else {
            OllamaStatus(
                status = "model_not_ready",
                model = model,
                detail =
                    "Ollama is running but the model is not yet downloaded. " +
                        "LLM reviews will be unavailable until the download completes.",
            )
        }
    }
}
