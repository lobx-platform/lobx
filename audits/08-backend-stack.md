# Backend Stack Audit

Blind code review of `back/` -- no prior context, evaluated purely on what the code says.

---

## 1. Current Tech Stack and Versions

| Layer | Choice | Version Constraint |
|-------|--------|--------------------|
| Language | Python | >=3.11 |
| HTTP framework | FastAPI | <0.116.0 |
| ASGI toolkit | Starlette | <0.41.0 (pinned explicitly) |
| Real-time transport | python-socketio[asgi] | unpinned |
| Data validation | Pydantic | unpinned (v2 implied by `model_dump`) |
| ASGI server | Uvicorn | unpinned |
| HTTP client | httpx, aiohttp (>=3.13.2), requests | mixed async/sync |
| Auth provider | Firebase Admin SDK | unpinned |
| Data analysis | pandas, polars, numpy, matplotlib | unpinned |
| Workflow orchestration | Prefect | unpinned |
| Container runtime | Docker (python:3.11-slim) | -- |
| Package manager | uv | latest (copied from ghcr.io/astral-sh/uv) |
| Ordered data structures | sortedcontainers | unpinned |

**Observations:**
- FastAPI and Starlette have upper-bound pins (`<0.116.0`, `<0.41.0`) but everything else floats. A lock file (`uv.lock`) exists so builds are reproducible, but the `pyproject.toml` constraints are loose enough that a `uv lock --upgrade` could pull breaking changes in socketio, pydantic, or firebase-admin.
- Three HTTP client libraries (`httpx`, `aiohttp`, `requests`) coexist. `requests` is synchronous and will block the event loop if called from async code.
- `prefect` is listed but no Prefect flows/tasks appear in the reviewed files -- possibly dead weight or used in an unreviewed module.

---

## 2. Is FastAPI + python-socketio the Right Choice?

### What works well

- **FastAPI for the REST surface** is a strong fit. The admin CRUD, login endpoints, and metrics downloads are standard request/response patterns. FastAPI's automatic OpenAPI docs, Pydantic integration, and dependency injection (`Depends(get_current_user)`) are used throughout and add real value.
- **python-socketio for the trading channel** solves the right problem: it gives you named events (`place_order`, `cancel_order`, `join_market`), rooms (one per market), and automatic reconnection -- all things a raw WebSocket handler would have to reinvent.
- The `socketio.ASGIApp(sio, other_asgi_app=_fastapi_app)` pattern keeps both protocols on a single port, which simplifies deployment behind a reverse proxy.

### Where it strains

| Concern | Detail |
|---------|--------|
| **Single-process ceiling** | All state (`_sessions`, `market_handler`, `trader_locks`, `base_settings`, `accumulated_rewards`, `lab_trader_map`) lives in Python dicts. There is no external state store. This means: (a) you cannot scale horizontally -- a second uvicorn worker sees different state; (b) a process crash loses everything; (c) `--reload` in production (present in the Dockerfile CMD) restarts the process and wipes all markets mid-trade. |
| **python-socketio scaling** | Scaling Socket.IO past a single server requires a pub/sub backend (Redis adapter). The current code has no adapter configured, so even if you ran multiple workers, rooms would not synchronize. ([Scaling Socket.IO](https://ably.com/topic/scaling-socketio), [python-socketio #1328](https://github.com/miguelgrinberg/python-socketio/discussions/1328)) |
| **Blocking polling loops** | `join_market` contains `for _ in range(60): await asyncio.sleep(1)` -- a 60-second busy-wait per connecting client. With 30 concurrent joiners, that is 30 long-lived coroutines polling every second. This should be an `asyncio.Event.wait()`. |
| **Fire-and-forget tasks** | `asyncio.create_task(trader_manager.launch())` in multiple places with no error handling or task tracking. If `launch()` raises, the exception is silently swallowed. |
| **No backpressure** | There is no mechanism to reject or queue orders when the order book processor is overloaded. Every `place_order` event acquires a per-trader lock and calls directly into the matching engine. |

### Verdict

FastAPI + python-socketio is **adequate for a research/lab platform with <50 concurrent users on a single server**. It is not suitable as-is for anything described as "production trading" -- but that may not be the goal. The critical issue is not the framework choice but the in-memory-only state and lack of persistence.

---

## 3. Better Alternatives in 2026?

### If staying in Python

| Option | Why consider | Why not |
|--------|-------------|---------|
| **[Litestar](https://litestar.dev/)** | Faster than FastAPI in benchmarks (msgspec serialization), built-in dependency injection, first-class WebSocket support, no Starlette coupling. Would eliminate the need for a separate socketio library. ([Litestar vs FastAPI](https://betterstack.com/community/guides/scaling-python/litestar-vs-fastapi/)) | Smaller ecosystem, fewer third-party examples. Migration cost from FastAPI is moderate. |
| **Django Channels** | Battle-tested WebSocket layer, channel-layer abstraction enables horizontal scaling without Socket.IO's Redis adapter, strong ORM for persistence. ([Framework comparison](https://rollbar.com/blog/python-backend-frameworks/)) | Heavier framework, ORM is not needed if you want to stay schema-free, slower raw throughput. |
| **Sanic** | Mature async framework, built-in WebSocket support, production-proven at scale. | Less type-safety tooling than FastAPI/Litestar. |

### If willing to leave Python for the hot path

| Option | Why consider |
|--------|-------------|
| **Rust (Axum + tokio-tungstenite)** | NautilusTrader (the leading open-source trading engine) uses Rust for its core runtime precisely because Python's GIL and per-coroutine overhead limit throughput. If order matching latency matters, Rust or C++ is the right answer. ([NautilusTrader](https://nautilustrader.io/)) |
| **Elixir (Phoenix Channels)** | Purpose-built for millions of concurrent WebSocket connections. The BEAM VM eliminates the need for external pub/sub. |

### Recommendation

For a research/experimental economics platform, **stay with FastAPI + python-socketio** but fix the architectural issues (see Section 6). The framework is not the bottleneck -- the in-memory state model is. If you later need >100 concurrent markets, Litestar with native WebSocket rooms would be the most natural Python migration path.

---

## 4. Code Quality Assessment

### Strengths

- **Clean separation of concerns**: The refactor into `core/handlers.py` (event-driven architecture with `MessageBus`, typed events, handler classes) is well-structured. The `MarketOrchestrator` pattern cleanly separates order processing, broadcasting, pricing, and trader management.
- **Pydantic models are comprehensive**: `TradingParameters` has 30+ fields with validators, type hints, descriptions, and sensible defaults. The `field_validator` for `predefined_goals` handles both string and list input gracefully.
- **Adapter pattern**: `SimpleMarketHandler` wraps `SessionManager` with backward-compatible properties. This is a clean migration strategy.
- **Socket.IO event handlers** are concise and follow a consistent pattern (lookup session -> lookup trader_manager -> lookup trader -> act).

### Issues

#### Security (Critical)

| Issue | Location | Severity |
|-------|----------|----------|
| **Admin password defaults to `"admin"`** | `api/auth.py:9` -- `ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")` | CRITICAL |
| **Admin password returned in login response** | `api/routes/auth.py:70` -- `"token": ADMIN_PASSWORD` sends the raw password back to the client | HIGH |
| **CORS allows all origins** | `endpoints.py:29` and `socketio_server.py:38` -- `allow_origins=["*"]` / `cors_allowed_origins="*"` | HIGH |
| **No rate limiting** | No rate limiting on login, order placement, or admin endpoints | MEDIUM |
| **Admin list hardcoded** | `api/routes/trading.py:149,169` -- `username in ['venvoooo', 'asancetta', ...]` duplicated instead of using `params.admin_users` | MEDIUM |
| **Ngrok authtoken in docker-compose.yml** | `docker-compose.yml:93` -- secret committed to version control | HIGH |
| **Prolific users auto-created without validation** | `socketio_server.py:85-91` -- any `prolific_pid` string creates a valid user | MEDIUM |

#### Error Handling

- **Bare `except Exception`** in multiple places (`admin.py:146`, `trading.py:237`) that swallow errors and return generic 500s, making debugging impossible.
- **`print()` instead of `logger`** in several locations (`socketio_server.py:119,151,226`, `admin.py:50,189`). Mix of `print()`, `logger.info()`, `logger.debug()`, and `logger.warning()` with no consistent strategy.
- **Silent failures in auth**: `get_current_user` extracts trader_id from URL path via string splitting (`path.split("/")`) -- fragile and will break if URL structure changes.

#### Async Patterns

- **Race condition in lock creation**: Both `_get_or_create_trader_lock` (socketio_server.py:97) and `get_trader_lock` (shared.py:42) have a TOCTOU race -- two coroutines can check `if trader_id not in trader_locks` simultaneously and create two different locks. Should use `setdefault()`.
- **`--reload` in production Dockerfile**: `Dockerfile.back:14` runs uvicorn with `--reload`, which uses file watchers and restarts the process on any file change. This will crash live markets.
- **Deprecated `on_event("startup")`**: FastAPI's `@app.on_event("startup")` is deprecated in favor of lifespan context managers.
- **No graceful shutdown**: There is no shutdown handler to clean up running markets, cancel background tasks, or notify connected clients before the process exits.

#### Typing

- Typing is inconsistent. `core/handlers.py` and `core/data_models.py` are well-typed. Route handlers are partially typed (return types are never annotated). The `shared.py` module uses `Dict[str, dict]` (lowercase `dict` as value type) which loses type information.

#### Code Duplication

- Admin user list appears in at least 3 places: `data_models.py` (as default for `admin_users` field), `trading.py:149`, and `trading.py:169`. The route handler hardcodes the list instead of reading from `params.admin_users`.
- `TradingParameters` instantiation with `**(base_settings or {})` is repeated ~5 times across route handlers.

---

## 5. Docker / Deployment Setup

### Dockerfile.back

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .
ENV PYTHONPATH=/app
CMD uv run uvicorn api.endpoints:app --host 0.0.0.0 --port 8000 --root-path ${ROOT_PATH:-/api} --reload
```

**Issues:**

| Issue | Impact |
|-------|--------|
| `--reload` in CMD | Restarts process on file changes in production. Will kill active markets. |
| No non-root user | Container runs as root. |
| No health check | Orchestrators (ECS, K8s) cannot detect if the app is hung. |
| `uv:latest` is non-deterministic | Build today and build tomorrow may get different uv versions. Pin a hash. |
| No `.dockerignore` evident | May copy `.git`, `__pycache__`, logs, tests into the image. |
| Single worker | `uvicorn` runs 1 worker. No `--workers` flag and no gunicorn. For a single-process-state app this is actually correct, but it means a CPU-bound request (matplotlib chart generation?) blocks everything. |

### docker-compose.yml

**Issues:**

| Issue | Impact |
|-------|--------|
| Source code bind-mounted in production service | `volumes:` mounts `./back/core`, `./back/api`, etc. into the `back` service. Combined with `--reload`, this is a dev setup masquerading as a deployable config. |
| Ngrok authtoken hardcoded | `2j4K90jU...` is a secret in plain text. Should be an env var or secret. |
| `back` service uses `app-network` but `front` does not | `front` has no `networks:` key, so it joins the default network. `front` and `back` may not be able to communicate depending on Docker Compose version. |
| No restart policy on `back` | If the backend crashes, it stays down. Should be `restart: unless-stopped`. |
| Logging driver on other services is `"none"` | The YAML anchor `&default-logging` sets `driver: "none"` -- any service using it silently drops all logs. |

### Deployment Architecture (inferred)

The frontend is deployed to Firebase Hosting (`firebase-dev.sh`), the backend runs in Docker with Ngrok providing the public tunnel. This is a viable lab/research setup but has no redundancy, no persistent storage, and no monitoring.

---

## 6. What to Keep vs. Change

### Keep

| Component | Why |
|-----------|-----|
| **FastAPI for REST** | Well-suited, good ecosystem, team knows it. |
| **python-socketio for real-time** | Works fine at research scale, rooms model fits the market abstraction. |
| **Pydantic data models** | `TradingParameters` and `Order` are well-designed, validated, and documented. |
| **Event-driven core** | `MessageBus` / `MarketOrchestrator` / typed event handlers is a clean architecture. |
| **uv for packaging** | Fast, modern, lock file works. |
| **`SimpleMarketHandler` adapter** | Good migration strategy that preserves backward compatibility. |

### Change

| Priority | Change | Effort |
|----------|--------|--------|
| **P0** | Remove `--reload` from Dockerfile CMD. Add a separate `docker-compose.dev.yml` for development. | 10 min |
| **P0** | Remove hardcoded ngrok authtoken and admin password default. Use Docker secrets or `.env` (already partially done). | 30 min |
| **P0** | Stop returning `ADMIN_PASSWORD` in the login response body. Issue a short-lived JWT or opaque session token instead. | 2 hr |
| **P1** | Replace polling loops in `join_market` with `asyncio.Event`. Create an event per session that is set when the market activates. | 1 hr |
| **P1** | Fix lock creation race: `trader_locks.setdefault(trader_id, asyncio.Lock())`. | 5 min |
| **P1** | Add structured logging (e.g., `structlog`) and remove all `print()` calls. | 2 hr |
| **P1** | Add a health check endpoint (`/health`) and `HEALTHCHECK` in Dockerfile. | 15 min |
| **P1** | Add graceful shutdown handler (lifespan context manager) that cleans up running markets. | 1 hr |
| **P2** | Deduplicate admin-user checks -- always read from `params.admin_users`, remove hardcoded lists. | 30 min |
| **P2** | Add response model annotations to all route handlers for auto-docs and type safety. | 2 hr |
| **P2** | Pin `python-socketio`, `pydantic`, `firebase-admin` versions in `pyproject.toml`. | 15 min |
| **P2** | Create a non-root user in Dockerfile. | 10 min |
| **P2** | Add `restart: unless-stopped` to the `back` service in docker-compose. | 1 min |
| **P3** | Add Redis-backed Socket.IO adapter for horizontal scaling if ever needed. | 2 hr |
| **P3** | Remove `requests` dependency; replace any sync HTTP calls with `httpx` async. | 1 hr |
| **P3** | Evaluate whether `prefect`, `matplotlib`, `pandas` are actually used in the hot path; if only for offline analysis, move to a separate `[analysis]` dependency group. | 30 min |

### If Starting Completely Fresh

If building this system from scratch in 2026 with the same requirements (experimental economics trading platform, <100 concurrent users, lab + Prolific recruitment):

1. **Keep FastAPI + python-socketio** -- the framework is not the problem.
2. **Add Redis** for session state and Socket.IO pub/sub from day one.
3. **Use SQLite or Postgres** for experiment metadata (treatments, participant assignments, market outcomes) instead of in-memory dicts.
4. **Separate the matching engine** into its own module with no I/O dependencies, making it unit-testable without mocking sockets.
5. **Use Pydantic `BaseSettings`** for configuration instead of a mutable `dict` (`base_settings`).
6. **Ship with Docker Compose profiles**: `docker compose --profile dev up` for hot-reload, `docker compose --profile prod up` for production.

---

## Sources

- [Scaling Socket.IO: Real-world challenges](https://ably.com/topic/scaling-socketio)
- [Scaling socketio server in FastAPI](https://github.com/miguelgrinberg/python-socketio/discussions/1328)
- [Litestar vs FastAPI](https://betterstack.com/community/guides/scaling-python/litestar-vs-fastapi/)
- [The Python Backend Framework Decision Guide for 2026](https://rollbar.com/blog/python-backend-frameworks/)
- [FastAPI vs Litestar (2025)](https://medium.com/@rameshkannanyt0078/fastapi-vs-litestar-2025-which-async-python-web-framework-should-you-choose-8dc05782a276)
- [NautilusTrader](https://nautilustrader.io/)
- [Socket.IO: The Complete Guide (2026 Edition)](https://dev.to/abanoubkerols/socketio-the-complete-guide-to-building-real-time-web-applications-2026-edition-c7h)
- [Python API Frameworks Benchmark](https://github.com/tanrax/python-api-frameworks-benchmark)
- [FastAPI vs Django vs Flask](https://betterstack.com/community/guides/scaling-nodejs/fastapi-vs-django-vs-flask/)
