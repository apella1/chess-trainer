package me.apella.chesstrainer.stats

import me.apella.chesstrainer.users.UserEntity
import me.apella.chesstrainer.users.UserService
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.mockito.ArgumentMatchers.any
import org.mockito.ArgumentMatchers.eq
import org.mockito.Mockito.mock
import org.mockito.Mockito.`when`
import org.springframework.jdbc.core.JdbcTemplate
import java.util.UUID

class StatsServiceTest {
    private val userService = mock(UserService::class.java)
    private val jdbcTemplate = mock(JdbcTemplate::class.java)
    private val statsService = StatsService(userService, jdbcTemplate)

    @Test
    fun `getWeaknesses returns ranked weaknesses by ratePerHundred descending with severity and frequency`() {
        val userId = UUID.randomUUID()
        val user =
            UserEntity(
                id = userId,
                chesscomUsername = "testuser",
                displayName = "Test User",
            )
        `when`(userService.findByUsername("testuser")).thenReturn(user)

        // Mock 200 total moves
        `when`(
            jdbcTemplate.queryForObject(
                org.mockito.ArgumentMatchers.contains("SELECT count(*) FROM moves"),
                eq(Int::class.java),
                eq(userId),
            ),
        ).thenReturn(200)

        // Mock 10 analyzed games
        `when`(
            jdbcTemplate.queryForObject(
                org.mockito.ArgumentMatchers.contains("SELECT count(*) FROM games"),
                eq(Int::class.java),
                eq(userId),
            ),
        ).thenReturn(10)

        // Mock mistake rows:
        // 6 hanging_piece (4 blunders, 2 mistakes) in middlegame -> rate = 6 * 100 / 200 = 3.0 / 100 moves
        // 2 missed_fork (2 mistakes) in opening -> rate = 2 * 100 / 200 = 1.0 / 100 moves
        val mockRows =
            listOf(
                mapOf("type" to "hanging_piece", "phase" to "middlegame", "classification" to "blunder", "cnt" to 4),
                mapOf("type" to "hanging_piece", "phase" to "middlegame", "classification" to "mistake", "cnt" to 2),
                mapOf("type" to "missed_fork", "phase" to "opening", "classification" to "mistake", "cnt" to 2),
            )
        `when`(
            jdbcTemplate.queryForList(
                org.mockito.ArgumentMatchers.contains("FROM mistakes m"),
                eq(userId),
                any(),
                any(),
            ),
        ).thenReturn(mockRows)

        val res = statsService.getWeaknesses("testuser")

        assertEquals("testuser", res.username)
        assertEquals(200, res.totalUserMoves)
        assertEquals(10, res.analyzedGames)
        assertEquals(2, res.weaknesses.size)

        // Ranked by rate descending
        val first = res.weaknesses[0]
        assertEquals("hanging_piece", first.type)
        assertEquals(6, first.count)
        assertEquals(3.0, first.ratePerHundred)
        assertEquals(75.0, first.frequencyPct) // 6 out of 8 total mistakes = 75.0%
        assertEquals(4, first.severity.blunders)
        assertEquals(2, first.severity.mistakes)
        assertEquals(0, first.severity.inaccuracies)

        val second = res.weaknesses[1]
        assertEquals("missed_fork", second.type)
        assertEquals(2, second.count)
        assertEquals(1.0, second.ratePerHundred)
        assertEquals(25.0, second.frequencyPct) // 2 out of 8 total mistakes = 25.0%
        assertEquals(0, second.severity.blunders)
        assertEquals(2, second.severity.mistakes)
        assertEquals(0, second.severity.inaccuracies)

        assertTrue(first.ratePerHundred >= second.ratePerHundred, "Ranked by ratePerHundred descending")
    }
}
