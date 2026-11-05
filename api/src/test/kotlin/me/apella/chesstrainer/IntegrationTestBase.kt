package me.apella.chesstrainer

import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.testcontainers.service.connection.ServiceConnection
import org.springframework.test.web.servlet.MockMvc
import org.testcontainers.containers.PostgreSQLContainer
import org.testcontainers.junit.jupiter.Container
import org.testcontainers.junit.jupiter.Testcontainers

/**
 * Base class for integration tests.
 * Starts a real PostgreSQL 16 container via Testcontainers and wires it
 * into Spring's datasource using @ServiceConnection.
 *
 * Auto-configures MockMvc for HTTP testing.
 * Subclasses mock external services (e.g. ChesscomClient) as needed.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Testcontainers
abstract class IntegrationTestBase {

    companion object {
        @Container
        @ServiceConnection
        @JvmStatic
        val postgres = PostgreSQLContainer("postgres:16")
    }
}
