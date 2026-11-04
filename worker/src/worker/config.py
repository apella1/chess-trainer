"""
Worker configuration loaded from environment variables.

All runtime configuration lives here. No other module hardcodes values.
The pydantic BaseSettings class reads from environment variables and .env files.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    db_url: str

    # Stockfish
    stockfish_path: str = "/usr/games/stockfish"

    # Engine analysis
    analysis_depth: int = 14
    analysis_multipv: int = 3

    # Ollama
    ollama_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "qwen3:8b"
    review_prompt_version: str = "v1"

    # Worker behaviour
    worker_poll_seconds: int = 5
    worker_instance_id: str = ""  # defaults to hostname if empty

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()  # type: ignore[call-arg]
