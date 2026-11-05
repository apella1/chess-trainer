# Build stage — runs as root only to compile; no artifact runs as root
FROM eclipse-temurin:25-jdk AS build
WORKDIR /app

# Copy gradle wrapper and build files first for layer caching
COPY gradle/ gradle/
COPY gradlew settings.gradle.kts build.gradle.kts ./
RUN chmod +x gradlew

# Download dependencies (cached unless build files change)
RUN ./gradlew dependencies --no-daemon -q

# Copy source and build
COPY src/ src/
RUN ./gradlew bootJar --no-daemon -x test

# Runtime stage
FROM eclipse-temurin:25-jre

# Create a dedicated non-root user and group.
# Using a fixed UID/GID (1001) makes the identity stable across rebuilds
# and avoids accidental overlap with host UIDs in bind-mount scenarios.
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/false --no-create-home appuser

WORKDIR /app

# Install curl for the Docker healthcheck.
# Done before switching user because apt-get requires root.
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy the jar and immediately set ownership so appuser can read it
COPY --from=build --chown=appuser:appgroup /app/build/libs/*.jar app.jar

# Drop privileges — everything from here runs as appuser
USER appuser

EXPOSE 8084

ENTRYPOINT ["java", "-jar", "app.jar"]
