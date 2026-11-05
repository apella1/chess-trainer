# Worker image: Python 3.12 slim + Stockfish
# Runs as a dedicated non-root user — root is only used during the build steps
# that require package installation.
FROM python:3.12-slim

# Create a dedicated non-root user before any application files are written.
# Fixed UID/GID 1001 for consistency across rebuilds.
RUN groupadd --gid 1001 workergroup && \
    useradd --uid 1001 --gid workergroup --shell /bin/false --no-create-home worker

WORKDIR /app

# Install system dependencies as root — required for apt-get and stockfish.
# stockfish binary ends up at /usr/games/stockfish (world-executable; readable by all users).
# curl is used for Ollama reachability checks in the worker.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        stockfish \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project metadata first for layer caching (still root, before chown)
COPY pyproject.toml ./

# Install Python dependencies system-wide so the non-root worker user can import them.
RUN uv pip install --system --no-cache \
    "psycopg[binary,pool]" \
    pydantic \
    pydantic-settings \
    httpx \
    tenacity \
    chess

# Copy source and transfer ownership to the worker user in one layer.
# Combining COPY + chown avoids a separate RUN chown which would double the layer size.
COPY --chown=worker:workergroup src/ src/

# Give the worker user ownership of the working directory
RUN chown -R worker:workergroup /app

# Drop privileges — all runtime code executes as worker (uid 1001)
USER worker

ENV PYTHONPATH=/app/src

CMD ["python", "-m", "worker.main"]
