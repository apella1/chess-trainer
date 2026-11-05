# Vite Dev Server Proxy

## Why It Exists

The React app runs on port 5176 (Vite dev server) and the Spring API runs on port 8084.
Browsers enforce same-origin policy: a page at `localhost:5176` cannot call `localhost:8084`
directly without CORS headers. Rather than relying solely on CORS, Vite proxies API
requests through its own dev server so the browser sees everything as same-origin.

## How It Works

```
Browser (localhost:5176)
  │
  ├── /api/status        ──→ Vite dev server ──→ http://api:8084/api/status
  ├── /actuator/health   ──→ Vite dev server ──→ http://api:8084/actuator/health
  └── /static/asset.js   ──→ Vite dev server ──→ served from Vite's own bundle
```

The browser never knows about port 8084. Every request goes to `localhost:5176`. Vite's dev
server inspects the path and either:
- Serves the request itself (static assets, HMR, React app)
- Forwards the request to the API backend (anything matching `/api` or `/actuator`)

## Configuration

The proxy is defined in `web/vite.config.ts`:

```typescript
server: {
  host: "0.0.0.0",   // required for Docker port binding
  port: 5176,
  proxy: {
    "/api": {
      target: process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8084",
      changeOrigin: true,
    },
    "/actuator": {
      target: process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8084",
      changeOrigin: true,
    },
  },
},
```

### Two modes

**Running in Docker Compose (production-like dev):**

The `VITE_API_PROXY_TARGET` env var is set in `docker-compose.yml`:
```yaml
environment:
  VITE_API_PROXY_TARGET: http://api:8084
```
Here, `api` is the Docker Compose service name. The Vite container resolves it via the
Compose internal DNS. The proxy forwards `/api/*` to `http://api:8084/api/*`.

**Running Vite directly on the host (without Docker):**

`VITE_API_PROXY_TARGET` is not set, so the fallback `http://localhost:8084` is used. This
assumes the Spring API is running on the host at port 8084.

### `changeOrigin: true`

This rewrites the `Host` header in the proxied request to match the target. Without it,
the API would see `Host: localhost:5176` which can confuse some frameworks. With it, the
API sees `Host: api:8084` (or `localhost:8084`) as expected.

## CORS Is Still Configured (Belt and Suspenders)

The Spring API has `CorsConfig.kt` that allows `http://localhost:5176`. This handles:
- Direct browser-to-API calls (e.g. if someone opens the API URL directly)
- The fallback scenario where Vite is not proxying

In normal Docker Compose operation, CORS headers are not exercised because the proxy
makes everything same-origin. But the config exists for robustness.

## Production (Static Build)

In production, Vite is not running. The React app is built to static files and served by
nginx (added in a later phase). The nginx config will proxy `/api` to the API container
just as Vite does in dev. The browser still sees same-origin requests.

## Why Not Just Use CORS and Skip the Proxy?

CORS alone would work, but the proxy has advantages:
- No preflight OPTIONS requests (slightly faster)
- No CORS misconfiguration risk
- The API doesn't need to know the frontend origin at build time
- Works identically in dev and prod (just the proxy implementation changes)
