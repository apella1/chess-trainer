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

data class TrendPoint(
    val period: String,
    val type: String,
    val count: Int,
    val totalMoves: Int,
    val ratePerHundred: Double,
)

data class TrendsResponse(
    val username: String,
    val periods: Int,
    val trends: List<TrendPoint>,
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

    /**
     * Trend data: mistake rates by type per rolling 2-week window.
     * Groups analyzed games by the month they were played, computes
     * mistake rate per 100 moves for each type per period.
     */
    fun getTrends(username: String, periods: Int = 6): TrendsResponse {
        val user = userService.findByUsername(username)
            ?: return TrendsResponse(username, 0, emptyList())

        val userId = user.id!!

        val rows = jdbcTemplate.queryForList(
            """
            SELECT
                to_char(g.played_at, 'YYYY-MM') as period,
                COALESCE(m.type, 'other') as type,
                count(m.id) as mistake_count,
                count(DISTINCT mo.id) as move_count
            FROM games g
            JOIN moves mo ON mo.game_id = g.id
                AND mo.color = CASE WHEN g.user_color = 'white' THEN 'white' ELSE 'black' END
            LEFT JOIN mistakes m ON m.game_id = g.id
            WHERE g.user_id = ?
              AND g.analysis_status = 'done'
              AND g.played_at IS NOT NULL
            GROUP BY period, type
            ORDER BY period DESC, mistake_count DESC
            """,
            userId,
        )

        val distinctPeriods = rows.map { it["period"] as String }.distinct().take(periods)
        val filtered = rows.filter { (it["period"] as String) in distinctPeriods }

        val trends = filtered.map { row ->
            val mistakeCount = (row["mistake_count"] as Number).toInt()
            val moveCount = (row["move_count"] as Number).toInt()
            TrendPoint(
                period = row["period"] as String,
                type = row["type"] as String,
                count = mistakeCount,
                totalMoves = moveCount,
                ratePerHundred = if (moveCount > 0) {
                    Math.round(mistakeCount * 100.0 / moveCount * 100) / 100.0
                } else 0.0,
            )
        }

        return TrendsResponse(username, distinctPeriods.size, trends)
    }
}
