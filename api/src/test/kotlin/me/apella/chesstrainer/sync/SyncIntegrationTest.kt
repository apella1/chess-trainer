package me.apella.chesstrainer.sync

import me.apella.chesstrainer.IntegrationTestBase
import org.awaitility.Awaitility
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.mockito.Mockito.`when`
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.http.MediaType
import org.springframework.test.context.bean.override.mockito.MockitoBean
import org.springframework.test.web.servlet.MockMvc
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.status
import tools.jackson.databind.ObjectMapper
import tools.jackson.databind.JsonNode
import java.time.Duration

/**
 * Integration tests for the chess.com sync feature.
 *
 * Uses fixture JSON (no live network) by mocking ChesscomClient.
 * Verifies:
 * - Sync imports games from fixture data
 * - Re-sync is idempotent (no duplicates)
 * - Malformed/empty archives are handled gracefully
 */
class SyncIntegrationTest : IntegrationTestBase() {

    @Autowired
    private lateinit var mockMvc: MockMvc

    @Autowired
    private lateinit var objectMapper: ObjectMapper

    @MockitoBean
    private lateinit var chesscomClient: ChesscomClient

    @Test
    fun `sync imports games and re-sync is idempotent`() {
        // Setup: mock chess.com API with fixture data
        `when`(chesscomClient.fetchArchives("testuser")).thenReturn(
            listOf("https://api.chess.com/pub/player/testuser/games/2024/01")
        )
        `when`(chesscomClient.fetchArchiveGames("https://api.chess.com/pub/player/testuser/games/2024/01")).thenReturn(
            loadFixtureGames()
        )

        // Act: start sync
        val syncResponse = mockMvc.perform(
            post("/api/sync")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""{"username": "testuser"}""")
        ).andExpect(status().isAccepted()).andReturn().response

        val syncId = objectMapper.readTree(syncResponse.contentAsString)["syncId"].asText()

        // Wait for sync to complete
        Awaitility.await()
            .atMost(Duration.ofSeconds(30))
            .until {
                val result = mockMvc.perform(get("/api/sync/$syncId"))
                    .andExpect(status().isOk())
                    .andReturn().response.contentAsString
                objectMapper.readTree(result)["status"].asText() == "done"
            }

        // Verify: games list contains 2 games
        val gamesResponse = mockMvc.perform(get("/api/games?username=testuser"))
            .andExpect(status().isOk())
            .andReturn().response.contentAsString
        val content = objectMapper.readTree(gamesResponse)["content"]
        assertEquals(2, content.size(), "Expected 2 games after sync")

        // Act again: re-sync (should add no new games)
        val syncResponse2 = mockMvc.perform(
            post("/api/sync")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""{"username": "testuser"}""")
        ).andExpect(status().isAccepted()).andReturn().response

        val syncId2 = objectMapper.readTree(syncResponse2.contentAsString)["syncId"].asText()

        Awaitility.await()
            .atMost(Duration.ofSeconds(30))
            .until {
                val result = mockMvc.perform(get("/api/sync/$syncId2"))
                    .andExpect(status().isOk())
                    .andReturn().response.contentAsString
                objectMapper.readTree(result)["status"].asText() == "done"
            }

        // Verify: still only 2 games (no duplicates)
        val gamesResponse2 = mockMvc.perform(get("/api/games?username=testuser"))
            .andExpect(status().isOk())
            .andReturn().response.contentAsString
        val content2 = objectMapper.readTree(gamesResponse2)["content"]
        assertEquals(2, content2.size(), "Expected 2 games after re-sync (no duplicates)")
    }

    @Test
    fun `malformed archive is handled gracefully`() {
        `when`(chesscomClient.fetchArchives("baduser")).thenReturn(
            listOf("https://api.chess.com/pub/player/baduser/games/2024/01")
        )
        `when`(chesscomClient.fetchArchiveGames("https://api.chess.com/pub/player/baduser/games/2024/01")).thenReturn(
            emptyList()
        )

        val syncResponse = mockMvc.perform(
            post("/api/sync")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""{"username": "baduser"}""")
        ).andExpect(status().isAccepted()).andReturn().response

        val syncId = objectMapper.readTree(syncResponse.contentAsString)["syncId"].asText()

        Awaitility.await()
            .atMost(Duration.ofSeconds(30))
            .until {
                val result = mockMvc.perform(get("/api/sync/$syncId"))
                    .andExpect(status().isOk())
                    .andReturn().response.contentAsString
                objectMapper.readTree(result)["status"].asText() == "done"
            }

        // No games should exist for this user
        val gamesResponse = mockMvc.perform(get("/api/games?username=baduser"))
            .andExpect(status().isOk())
            .andReturn().response.contentAsString
        val content = objectMapper.readTree(gamesResponse)["content"]
        assertTrue(content.isEmpty, "Expected 0 games for baduser")
    }

    private fun loadFixtureGames(): List<ChesscomGame> {
        val json = this::class.java.getResourceAsStream("/fixtures/games_response.json")!!
            .bufferedReader().use { it.readText() }
        return objectMapper.readValue(json, GamesResponse::class.java).games
    }
}
