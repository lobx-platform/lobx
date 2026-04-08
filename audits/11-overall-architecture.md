# Overall Architecture Audit

**Date:** 2026-04-08  
**Branch:** `refactor/core-rewrite`  
**Auditor:** External systems review (no prior context)

---

## Codebase Snapshot

| Metric | Value |
|--------|-------|
| Backend Python files | 47 |
| Backend LOC | ~9,200 |
| Frontend Vue/JS files | 44 |
| Frontend LOC | ~10,600 |
| Total LOC (app code) | ~19,800 |
| Test files | 7 (backend only) |
| Test LOC | ~1,500 |
| Test-to-code ratio | 0.08:1 |
| Docker services | 4 (back, front, front-deploy, ngrok) |
| CI/CD workflows | 1 (build + deploy) |

---

## 1. Monorepo: Is It the Right Approach?

**Verdict: Yes, and it's arguably the only sensible choice for this project.**

### Why it works

This is a 5-person academic team building a single product. The frontend and backend are tightly coupled -- they share a WebSocket protocol, identical data model names (`TradingParameters` on both sides), and deploy together. Splitting into separate repos would create overhead with zero benefit.

The 2026 industry consensus supports this: monorepos are now the default for small-to-medium teams, especially when AI-assisted development tools (which need full project context) are in play. Airbnb, Shopify, and Google all use monorepos for tightly-coupled services. The distinction between "monorepo" and "microservices" is a false dichotomy -- a monorepo can contain cleanly separated services that deploy independently.

### What to watch

- **The `back/` and `front/` separation is clean.** Each has its own dependency management (`pyproject.toml` / `package.json`), its own Dockerfile, and its own CI build step. This is textbook monorepo structure.
- **No shared code library.** There is no `shared/` or `common/` package for types/constants used by both front and back. This is fine at the current scale, but if the data model drifts (e.g., frontend using different field names than the backend `TradingParameters`), bugs will emerge. Consider a shared `types.yaml` or OpenAPI spec as a single source of truth if the API surface grows.

### Recommendation

Keep the monorepo. Do not split. If the project grows to multiple independently-deployable services (e.g., a separate analysis pipeline, a separate participant recruitment service), add them as top-level directories alongside `back/` and `front/`.

---

## 2. Deployment Architecture

**Current setup:**
```
GitHub Actions (CI)
  -> Build backend Docker image -> push to DockerHub
  -> SSH into Durham server -> docker compose pull + restart
  -> Build frontend (Vite) -> deploy to Firebase Hosting
  -> ngrok tunnel exposes backend at dthinkr.ngrok.app
```

**Verdict: Functional but fragile. Appropriate for the research stage, not for long-term use.**

### What works

- **Split deployment is smart.** Static frontend on Firebase Hosting (global CDN, free tier, zero-downtime deploys) and stateful backend on a dedicated server. This is the correct pattern for a WebSocket-heavy application where the backend must maintain in-memory state (order books, active markets).
- **Docker for the backend.** Reproducible builds, `uv sync` for fast Python dependency resolution, single-command local dev via `docker compose up`.
- **GitHub Actions CI/CD.** Automatic deploy on push to `main` -- simple, reliable.

### What's fragile

1. **ngrok as production infrastructure.** The ngrok authtoken is hardcoded in `docker-compose.yml` and `docker-compose.server.yml` (line 95 and line 44 respectively). ngrok is a tunneling service designed for development; it adds latency (~50-100ms per hop), has bandwidth limits on free/personal plans, and creates a single point of failure. For a trading experiment where millisecond-level order book updates matter and you need 20+ concurrent participants, ngrok is a risk.

2. **Hardcoded URLs.** The ngrok hostname `dthinkr.ngrok.app` is baked into `Dockerfile.front` (lines 16-17), the CI workflow (lines 68-69), and `docker-compose.yml`. Changing the backend URL requires editing 3+ files.

3. **No staging environment.** The CI pipeline deploys directly to production on every push to `main`. There is no staging/preview deployment, no smoke test before deploy, and no rollback mechanism beyond `git revert`.

4. **In-memory state with no persistence.** All market state (active sessions, order books, trader positions) lives in Python dicts inside `SessionManager` and `TraderManager`. A server restart or OOM kill loses everything. For 3-minute experiments this is acceptable; for batch runs of 2,205 markets, a crash at market 2,000 means re-running everything.

5. **Security exposure.** The ngrok authtoken is committed to version control in plaintext. The `ADMIN_PASSWORD` defaults to `"admin"` in production if the env var is not set. CORS is `allow_origins=["*"]`.

### Recommendations

| Priority | Action | Effort |
|----------|--------|--------|
| HIGH | Move ngrok authtoken to `.env` / GitHub secrets. It is currently in plaintext in committed files. | 30 min |
| HIGH | Set up a reverse proxy (Caddy or nginx) on the Durham server instead of ngrok. Get a proper domain + TLS cert. | 2-4 hours |
| MEDIUM | Add a staging deploy: Firebase preview channels for frontend (already supported), a second Docker Compose profile for staging backend. | 2 hours |
| MEDIUM | Add checkpoint/resume for batch experiments (write market results to disk after each market, allow resuming from last checkpoint). | 4 hours |
| LOW | Extract hardcoded URLs into a single `deploy.env` or CI variable matrix. | 1 hour |

---

## 3. Comparison to Academic Experiment Platforms

### oTree (Python/Django)

oTree is the dominant platform for behavioral economics experiments. It provides:
- Built-in participant management, session creation, payment tracking
- Page-based experiment flow (consent -> instructions -> task -> results)
- Built-in admin panel with real-time monitoring
- Heroku/Docker deployment
- Synchronous round-based games (not real-time order books)

**How LOBX compares:** LOBX is fundamentally different because it needs *real-time continuous trading* with sub-second order matching. oTree's page-based model cannot support a live order book. LOBX correctly chose to build a custom platform rather than fight oTree's abstractions.

**What LOBX should borrow from oTree:**
- oTree's session/participant management is rock-solid and well-tested. LOBX's `SessionManager` (308 LOC) is a simplified version of oTree's equivalent -- good.
- oTree exports data as CSV with one click. LOBX's data export (`/admin/download_*` endpoints, `logfiles_analysis.py`) exists but is less polished.
- oTree has extensive documentation and a large user community. LOBX's README is minimal.

### Empirica (JavaScript/React)

Empirica is designed for real-time multi-participant experiments. It provides:
- Built-in real-time data synchronization
- Automatic concurrency control
- React-based frontend with reactive state
- MongoDB for persistent storage
- Designed for games, negotiations, group decision-making

**How LOBX compares:** Empirica is the closest competitor in architecture. Both use WebSocket for real-time communication, both support multi-participant sessions, both have admin dashboards. The key difference is that LOBX has a *matching engine* (order book with price-time priority), which Empirica does not.

**What LOBX should borrow from Empirica:**
- Empirica uses a database (MongoDB) for state persistence. LOBX uses only in-memory state + JSON log files. Adding even SQLite for session/market metadata would prevent the "crash and lose everything" failure mode.
- Empirica's "flexible defaults" design philosophy -- provide sensible defaults that work out of the box, but allow everything to be overridden. LOBX's `TradingParameters` (458 LOC, dozens of fields) is the opposite: it exposes every knob, most of which experimenters never touch.

### ORSEE / hroot / LIONESS

These are participant recruitment and session management tools, not experiment platforms. They handle sign-up, scheduling, and payment. LOBX handles its own participant management via lab tokens, which is simpler but less featureful than these dedicated tools.

### Summary Table

| Feature | oTree | Empirica | LOBX |
|---------|-------|----------|------|
| Real-time trading | No | Possible but no matching engine | Yes (core feature) |
| State persistence | PostgreSQL | MongoDB | In-memory only |
| Participant management | Built-in, robust | Built-in | Lab tokens (simple) |
| Data export | CSV, one-click | API + export | JSON logs + API |
| Admin dashboard | Built-in | Built-in | Custom (AdminDashboard.vue) |
| Deployment | Heroku/Docker | Docker | Docker + Firebase + ngrok |
| Documentation | Extensive | Good | Minimal |
| Testing | Extensive | Good | Minimal |
| Community | Large (1000s of papers) | Growing (100s) | Internal only |

---

## 4. Testing Story

**Verdict: Critically underinvested. The test suite is almost entirely integration/smoke tests, not automated unit tests.**

### Current state

**Backend tests (7 files, ~1,500 LOC):**

| File | Type | What it tests | Runs against |
|------|------|---------------|-------------|
| `test_session_manager.py` | Unit-ish | Session join, role assignment, goal persistence | Imports `SessionManager` directly |
| `test_treatments.py` | Unit | Treatment YAML loading, merging | Imports `TreatmentManager` directly |
| `test_reward_calculation.py` | Unit | Reward math | Imports utility functions |
| `test_trading_lifecycle.py` | Integration | 40-trader x 4-market role persistence | Hits live HTTP endpoints |
| `test_lab_100_users.py` | Load test | 100 concurrent lab users | Hits live HTTP endpoints |
| `test_market_logging.py` | Integration | Log file correctness | Hits live HTTP endpoints |
| `test_cohort_persistence.py` | Integration | Cohort assignment (likely outdated after refactor) | Hits live HTTP endpoints |

**Frontend tests: None.** Zero test files. No vitest, jest, cypress, or playwright configuration.

**CI tests: None.** The GitHub Actions workflow builds and deploys but runs zero tests.

### What's missing

1. **Unit tests for the matching engine.** `trading_platform.py`, `orderbook_manager.py`, `transaction_manager.py`, and `handlers.py` are the most critical code in the system (they determine whether trades execute correctly, whether prices are right, whether the order book is consistent). There are no tests for any of them.

2. **Unit tests for trader behavior.** `InformedTrader` (640 LOC) and `NoiseTrader` have complex logic for order placement timing, price calculation, and inventory management. Untested.

3. **WebSocket/Socket.IO integration tests.** The real-time communication layer (`socketio_server.py`, 350 LOC) is entirely untested. Connection, authentication, event routing, market joining, order placement via WebSocket -- all untested.

4. **Frontend tests.** No component tests, no store tests, no e2e tests. The trading dashboard (`TradingDashboard.vue`, 833 LOC) is the most complex component and has zero test coverage.

5. **CI test gate.** Deployments proceed even if tests fail (because no tests run in CI).

### Recommendations

| Priority | Action | Effort |
|----------|--------|--------|
| CRITICAL | Add unit tests for the order book / matching engine. This is financial software -- incorrect matching means incorrect experiment results. | 8-12 hours |
| HIGH | Add `pytest` to CI pipeline (even just running existing tests). Block deploy on test failure. | 1 hour |
| HIGH | Add a single e2e smoke test: create lab link -> login -> onboard -> trade -> verify summary. Use pytest + aiohttp or playwright. | 4 hours |
| MEDIUM | Add vitest for frontend store logic (auth, session, orders). | 4 hours |
| LOW | Add test fixtures / factories for `TradingParameters`, `WaitingUser`, etc. to reduce boilerplate in tests. | 2 hours |

---

## 5. Developer Experience

**Verdict: Reasonable for the project lead, rough for a new team member.**

### Onboarding friction points

1. **No `.env.example`.** A new developer must figure out which environment variables are needed by reading `docker-compose.yml`, the CI workflow, and `auth.py`. Required variables include Firebase credentials (7 variables), `OPENROUTER_API_KEY`, `TURNSTILE_SECRET_KEY`, `ADMIN_PASSWORD`, and a Firebase service account JSON file. There is a `.env` file but it is gitignored.

2. **Firebase dependency for development.** The backend imports `firebase-admin` and requires `GOOGLE_APPLICATION_CREDENTIALS` pointing to a service account JSON. A new developer cannot start the backend without obtaining Firebase credentials from the project lead. This is a significant barrier.

3. **No Makefile / justfile / task runner.** `run.sh` exists and is helpful, but it only covers Docker-based workflows. There is no command for running tests, linting, formatting, or generating lab links from the command line.

4. **Large dependency surface.** The backend `pyproject.toml` lists 20 dependencies including `prefect` (a workflow orchestration framework), `matplotlib`, `pandas`, `polars`, `google-api-python-client`, and `firebase-admin`. Several of these appear to be unused or used only in analysis scripts. A fresh `uv sync` downloads hundreds of packages.

5. **No code formatting/linting in CI.** No `ruff`, `black`, `isort`, or `eslint` enforcement. The `.gitignore` mentions eslint config exists (`front/config/eslint.config.js`) but it is not run in CI.

6. **Numbered page components.** The onboarding pages are named `0.vue` through `8.vue` (with `5.vue` missing). This naming convention provides no information about what each page does. A new developer must open each file to understand the onboarding flow.

### What works well

- **`run.sh dev`** is a genuine one-command startup. Docker Compose handles both services with hot-reload.
- **The backend module structure** (`api/routes/`, `core/`, `traders/`, `utils/`) is logical and discoverable.
- **The `CORE.md` refactoring plan** is exceptionally detailed -- better documentation than most production codebases. It serves as both a design doc and a TODO list.
- **The existing audit series** (`audits/01-06`) provides deep analysis of specific subsystems, which is unusual and valuable for a research project.

### Recommendations

| Priority | Action | Effort |
|----------|--------|--------|
| HIGH | Create `.env.example` with all required variables and comments. | 30 min |
| HIGH | Make Firebase optional for local dev. Use a flag like `AUTH_MODE=local` that bypasses Firebase and uses only lab tokens + admin password. | 2 hours |
| MEDIUM | Add a `Makefile` or `justfile` with targets: `dev`, `test`, `lint`, `format`, `lab-links`, `batch`. | 1 hour |
| MEDIUM | Rename page components: `0.vue` -> `ConsentPage.vue`, `1.vue` -> `WelcomePage.vue`, etc. | 30 min |
| LOW | Audit `pyproject.toml` dependencies. Remove `prefect`, `matplotlib`, `pandas`, `polars` if they are not used in the core runtime. Move analysis-only deps to an `[optional-dependencies]` group. | 1 hour |

---

## 6. If Rebuilding from Scratch in 2026

Given what this platform actually does -- run 3-minute continuous double auction experiments with 1 human + N bots, collect order-level data, export for analysis -- here is what a clean-sheet architecture would look like.

### Core Design Principles

1. **The matching engine is the product.** Everything else is scaffolding. The order book, price-time priority, and trade execution logic should be the most tested, most documented, most reviewed code in the project.

2. **Experiments are stateless workflows.** Each experiment run should be a pure function: `(config, random_seed) -> (log_file)`. No mutable global state. No in-memory session tracking. The server orchestrates, but each market is an independent unit.

3. **Separate the experiment runner from the participant UI.** The experiment runner (create market, spawn bots, run for N seconds, save log) should work without any frontend. The participant UI is an optional interface for human subjects.

### Proposed Architecture

```
trading-platform/
  engine/              # Pure Python, zero dependencies
    orderbook.py       # LOB with price-time priority (200 LOC)
    matcher.py         # Match engine: order in -> trades out (100 LOC)
    types.py           # Order, Trade, Side, OrderBook dataclasses (50 LOC)
    test_orderbook.py  # 100% coverage, property-based tests

  bots/                # Bot strategies (depend on engine only)
    noise.py
    informed.py
    base.py

  server/              # FastAPI + Socket.IO (depends on engine + bots)
    app.py             # Entry point, middleware
    routes/
      experiment.py    # POST /experiment/create, GET /experiment/:id
      admin.py         # Settings, data export
      auth.py          # Lab token + admin password (no Firebase)
    ws/
      trading.py       # Socket.IO handlers for real-time trading
    models.py          # Pydantic schemas (ExperimentConfig, MarketResult)
    experiment_runner.py  # Orchestrates: create market, add bots, run, save

  ui/                  # Vue 3 + Vite (depends on server API only)
    src/
      pages/
        ConsentPage.vue
        TradingView.vue
        SummaryPage.vue
        AdminPanel.vue
      stores/
      composables/

  data/                # Experiment output (gitignored)
    experiments/
      2026-04-08_exp001/
        config.yaml
        market_001.jsonl
        market_002.jsonl
        summary.csv
```

### Technology Choices

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python 3.12+ | Team expertise, scientific ecosystem |
| Web framework | FastAPI | Already in use, async-native, good WebSocket support |
| Real-time | Socket.IO (python-socketio) | Already in use, room-based pub/sub, reconnection handling |
| Frontend | Vue 3 + Vite | Already in use, team knows it |
| State persistence | SQLite (via `aiosqlite`) | Zero-config, single file, survives restarts. Store experiment metadata, participant sessions, market results. Keep order-level data in JSONL files for analysis. |
| Auth | Lab tokens + admin password | Exactly what the refactored codebase already does. No Firebase. |
| Deployment | Docker Compose on a VPS with Caddy reverse proxy | Caddy provides automatic HTTPS. No ngrok. Domain like `lobx.rhul.ac.uk` or `lobx.research.io`. |
| Testing | pytest + hypothesis (property-based) for engine, vitest for frontend | The matching engine is the one place where correctness is non-negotiable. Property-based tests catch edge cases humans miss. |
| CI | GitHub Actions: lint -> test -> build -> deploy (with staging) | Block deploy on test failure. Preview deploys for PRs. |

### Key Differences from Current Architecture

1. **The `engine/` package has zero web dependencies.** It can be imported in a Jupyter notebook for analysis, used in a batch script, or called from the server. Currently, the order book logic is intertwined with WebSocket communication and trader management.

2. **SQLite replaces in-memory dicts for session tracking.** A server restart no longer loses all state. Experiment results are durable from the moment they're produced.

3. **No Firebase.** Firebase adds complexity (service account management, SDK dependencies, auth flow) for a feature the team does not use (Google sign-in was removed in the refactor). Lab tokens and admin passwords are sufficient.

4. **Structured experiment output.** Instead of scattered JSON files in `back/logs/`, each experiment run gets a directory with a config file and per-market JSONL logs. This makes analysis reproducible: you can always answer "what config produced this data?"

5. **Property-based tests for the matching engine.** Instead of testing "does this specific order sequence produce this specific result," test invariants: "the order book never has crossed prices," "total money is conserved across all trades," "orders always execute at the posted price or better." These tests catch bugs that example-based tests miss.

### Migration Path

The good news: the current refactor (`CORE.md`) is already moving in this direction. The session manager is simplified, dead trader types are removed, Firebase is being phased out. The remaining gap is:

1. Extract the matching engine into a standalone, heavily-tested module.
2. Add SQLite for session/experiment metadata.
3. Replace ngrok with a proper reverse proxy.
4. Add tests to CI.

These are incremental changes, not a rewrite. The current architecture is 80% of the way to the ideal.

---

## Summary Scorecard

| Dimension | Score | Notes |
|-----------|-------|-------|
| Monorepo structure | A | Clean separation, correct choice for team size |
| Deployment | C+ | Works but fragile (ngrok, no staging, no rollback) |
| vs. Academic platforms | B+ | Solves a problem oTree/Empirica cannot; lacks their polish |
| Testing | D | Near-zero coverage on critical paths (matching engine, WebSocket) |
| Developer experience | B- | One-command start is good; no .env.example, Firebase barrier |
| Architecture cleanliness | B | Post-refactor structure is sensible; engine not yet decoupled |

**Bottom line:** The platform is well-suited to its purpose (running trading experiments for academic papers). The monorepo structure and basic deployment work. The two highest-leverage investments are (1) testing the matching engine and (2) replacing ngrok with proper infrastructure. The refactoring plan in `CORE.md` addresses most other concerns.
