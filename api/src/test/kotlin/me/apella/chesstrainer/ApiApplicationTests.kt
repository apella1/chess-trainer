package me.apella.chesstrainer

import org.junit.jupiter.api.Test
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.testcontainers.service.connection.ServiceConnection
import org.testcontainers.postgresql.PostgreSQLContainer
import org.testcontainers.junit.jupiter.Container
import org.testcontainers.junit.jupiter.Testcontainers

/**
 * Smoke test: verifies the Spring application context loads without errors
 * against a real PostgreSQL database (via Testcontainers).
 *
 * @ServiceConnection wires the container's JDBC URL, username, and password
 * directly into Spring's datasource configuration — no manual property overrides needed.
 */
@SpringBootTest
@Testcontainers
class ApiApplicationTests {

    companion object {
        @Container
        @ServiceConnection
        @JvmStatic
        val postgres = PostgreSQLContainer("postgres:16")
    }

    @Test
    fun contextLoads() {
        // Verifies the application context starts and Flyway migrations run cleanly
    }
}
