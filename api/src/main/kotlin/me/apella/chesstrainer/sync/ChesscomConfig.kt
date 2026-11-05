package me.apella.chesstrainer.sync

import org.springframework.beans.factory.annotation.Value
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.web.client.RestClient

@Configuration
class ChesscomConfig {

    @Value("\${chesscom.user-agent:ChessTrainer/1.0}")
    private lateinit var userAgent: String

    @Bean
    fun chesscomRestClient(): RestClient {
        return RestClient.builder()
            .baseUrl("https://api.chess.com")
            .defaultHeader("User-Agent", userAgent)
            .build()
    }
}
