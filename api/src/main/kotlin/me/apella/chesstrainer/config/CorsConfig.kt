package me.apella.chesstrainer.config

import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.web.cors.CorsConfiguration
import org.springframework.web.cors.UrlBasedCorsConfigurationSource
import org.springframework.web.filter.CorsFilter

/**
 * CORS configuration.
 *
 * Allows the Vite dev server (localhost:5176) to call the API.
 * In production, tighten allowedOrigins to the actual app domain.
 */
@Configuration
class CorsConfig {
    @Bean
    fun corsFilter(): CorsFilter {
        val config =
            CorsConfiguration().apply {
                allowedOrigins = listOf("http://localhost:5176")
                allowedMethods = listOf("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
                allowedHeaders = listOf("*")
                allowCredentials = true
                maxAge = 3600L
            }

        val source = UrlBasedCorsConfigurationSource()
        source.registerCorsConfiguration("/api/**", config)

        return CorsFilter(source)
    }
}
