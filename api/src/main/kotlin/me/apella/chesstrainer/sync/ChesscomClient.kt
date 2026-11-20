package me.apella.chesstrainer.sync

import com.fasterxml.jackson.annotation.JsonIgnoreProperties
import com.fasterxml.jackson.annotation.JsonProperty
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Component
import org.springframework.web.client.HttpClientErrorException
import org.springframework.web.client.RestClient

/** Response from GET /pub/player/{username}/games/archives */
@JsonIgnoreProperties(ignoreUnknown = true)
data class ArchivesResponse(
    val archives: List<String> = emptyList(),
)

/** A single game from a monthly archive */
@JsonIgnoreProperties(ignoreUnknown = true)
data class ChesscomGame(
    val url: String? = null,
    val pgn: String = "",
    @JsonProperty("time_control") val timeControl: String? = null,
    @JsonProperty("end_time") val endTime: Long? = null,
    @JsonProperty("time_class") val timeClass: String? = null,
    val uuid: String? = null,
    val white: ChesscomPlayer = ChesscomPlayer(),
    val black: ChesscomPlayer = ChesscomPlayer(),
)

@JsonIgnoreProperties(ignoreUnknown = true)
data class ChesscomPlayer(
    val rating: Int? = null,
    val result: String? = null,
    val username: String? = null,
    @JsonProperty("@id") val id: String? = null,
    val uuid: String? = null,
)

/** Response from GET {archive_url} */
@JsonIgnoreProperties(ignoreUnknown = true)
data class GamesResponse(
    val games: List<ChesscomGame> = emptyList(),
)

@Component
class ChesscomClient(
    private val chesscomRestClient: RestClient,
) {
    private val log = LoggerFactory.getLogger(ChesscomClient::class.java)

    /**
     * Fetch the list of archive URLs for a player.
     * Returns an empty list if the player has no archives or the request fails.
     */
    fun fetchArchives(username: String): List<String> =
        try {
            val response =
                chesscomRestClient
                    .get()
                    .uri("/pub/player/{username}/games/archives", username.lowercase())
                    .retrieve()
                    .body(ArchivesResponse::class.java)
            response?.archives ?: emptyList()
        } catch (ex: HttpClientErrorException.NotFound) {
            log.warn("Player {} not found on chess.com", username)
            emptyList()
        } catch (ex: Exception) {
            log.error("Error fetching archives for {}: {}", username, ex.message)
            emptyList()
        }

    /**
     * Fetch games from a single archive URL.
     * Returns an empty list if the archive is empty, malformed, or the request fails.
     */
    fun fetchArchiveGames(archiveUrl: String): List<ChesscomGame> =
        try {
            val response =
                chesscomRestClient
                    .get()
                    .uri(archiveUrl)
                    .retrieve()
                    .body(GamesResponse::class.java)
            response?.games ?: emptyList()
        } catch (ex: HttpClientErrorException.NotFound) {
            log.debug("Archive {} returned 404, skipping", archiveUrl)
            emptyList()
        } catch (ex: Exception) {
            log.error("Error fetching archive {}: {}", archiveUrl, ex.message)
            emptyList()
        }
}
