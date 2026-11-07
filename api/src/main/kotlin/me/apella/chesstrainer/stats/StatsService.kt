package me.apella.chesstrainer.stats

import me.apella.chesstrainer.users.UserService
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.stereotype.Service

data class WeaknessEntry(
    val type: String,
    val count: Int,
    val ratePerHundred: Double,
    val phases: Map<String, Int>,
)

data class WeaknessesResponse(
    val username: String,
    val totalUserMoves: Int,
    val analyzedGames: Int,
    val weaknesses: List<WeaknessEntry>,
)

@Service
class StatsService(
    private val userService: UserService,
    private val jdbcTemplate: JdbcTemplate,
) {

    fun getWeaknesses(username: String): WeaknessesResponse {
        val user = userService.findByUsername(username)
            ?: return WeaknessesResponse(username, 0, 0, emptyList())

        val userId = user.id!!

        // Total user moves across all analyzed games (only user's own moves)
        val totalMoves = jdbcTemplate.queryForObject(
            """
            SELECT count(*) FROM moves mo
            JOIN games g ON mo.game_id = g.id
            WHERE g.user_id = ?
              AND g.analysis_status = 'done'
              AND mo.color = CASE WHEN g.user_color = 'white' THEN 'white' ELSE 'black' END
            """,
            Int::class.java,
            userId,
        ) ?: 0

        // Analyzed game count
        val analyzedGames = jdbcTemplate.queryForObject(
            "SELECT count(*) FROM games WHERE user_id = ? AND analysis_status = 'done'",
            Int::class.java,
            userId,
        ) ?: 0

        if (totalMoves == 0) {
            return WeaknessesResponse(username, 0, analyzedGames, emptyList())
        }

        // Mistakes grouped by type and phase
        val rows = jdbcTemplate.queryForList(
            """
            SELECT COALESCE(type, 'other') as type,
                   COALESCE(phase, 'middlegame') as phase,
                   count(*) as cnt
            FROM mistakes
            WHERE user_id = ?
            GROUP BY type, phase
            ORDER BY type, phase
            """,
            userId,
        )

        // Aggregate by type
        val byType = mutableMapOf<String, MutableMap<String, Int>>()
        for (row in rows) {
            val type = row["type"] as String
            val phase = row["phase"] as String
            val cnt = (row["cnt"] as Number).toInt()
            byType.getOrPut(type) { mutableMapOf() }[phase] =
                (byType[type]?.get(phase) ?: 0) + cnt
        }

        val weaknesses = byType.map { (type, phases) ->
            val total = phases.values.sum()
            val rate = total * 100.0 / totalMoves
            WeaknessEntry(
                type = type,
                count = total,
                ratePerHundred = Math.round(rate * 100.0) / 100.0,
                phases = phases,
            )
        }.sortedByDescending { it.ratePerHundred }

        return WeaknessesResponse(
            username = username,
            totalUserMoves = totalMoves,
            analyzedGames = analyzedGames,
            weaknesses = weaknesses,
        )
    }
}
