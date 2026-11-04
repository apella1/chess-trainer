# Worker image: Python 3.12 slim + Stockfish + python-chess dependencies
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
# stockfish: chess engine
# curl: for health checks and Ollama connectivity tests
RUN apt-get update && apt-get install -y --no-install-recommends \
    stockfish \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project metadata first for layer caching
COPY pyproject.toml ./

# Install dependencies (no editable install needed for the container)
RUN uv pip install --system --no-cache \
    psycopg[binary,pool] \
    pydantic \
    pydantic-settings \
    httpx \
    tenacity

# Copy source
COPY src/ src/

# Run the worker
ENV PYTHONPATH=/app/src
CMD ["python", "-m", "worker.main"]
