# LOBX Platform — Core Rewrite Plan

## Why

The platform grew organically to serve Prolific, Firebase, lab tokens, 8 bot types, agentic LLM traders, and complex cohort/treatment logic. After running actual experiments, we know what's needed. The rest is dead weight that causes bugs.

**The real problem**: `session_manager.py` (852 LOC) is incomprehensible. Cohorts, treatment groups, market_sizes, permanent_roles, historical_markets — nobody can trace the flow. This caused every major bug in the April 1 experiment.

**Current**: ~13,700 LOC backend, ~8,900 LOC frontend.
**Target**: Cut 40-50%. Make the experiment flow obvious to anyone reading the code.

## Principles

1. **Lab-first** — Lab token is the only user auth. Admin gets a simple password login (env var `ADMIN_PASSWORD`, Bearer token).
2. **Three traders only** — Human + Informed + Noise. Everything else is deleted.
3. **Obvious experiment flow** — One user → one session → N markets. No cohort system. No market_sizes. No permanent_roles.
4. **One file, one job** — No file over 300 lines.
5. **Delete, don't comment** — If it's not needed, it's gone.

## Frontend Design

All frontend pages will be rewritten with a fresh visual identity. See `FRONTEND-DESIGN.md` for the design system and aesthetic guidelines. Onboarding **content** (consent text, instructions, questions) stays unchanged; the **look and feel** is redesigned.

## The Core Simplification: Experiment Flow

### Current (broken complexity)
```
User login → treatment_group assigned → _get_or_assign_cohort() →
  market_sizes checked → cohort_members tracked → cohort_sessions created →
  _find_or_create_cohort_session() → _create_session_slots() →
  predefined_goals shuffled → RoleSlot assigned → mark_user_ready() →
  _can_user_join() checks user_historical_markets → start_trading_session() →
  treatment_manager.get_merged_params() → cohort_treatment_overrides applied →
  TraderManager created → active_markets tracked → cleanup_finished_markets() →
  permanent_speculators/permanent_informed_goals persisted → next market...
```

### Target (simple)
```
User login (lab token) → Session created (1 user, 1 session)
  → For each market (0 to N-1):
      get treatment params for this market index
      create market (Human + Informed + Noise)
      run 3 minutes
      save log
      show summary
  → Done
```

### What changes
| Concept | Before | After |
|---------|--------|-------|
| Session | Cohort-based, multi-user | One user = one session |
| Treatment | cohort_treatment_overrides + treatment_manager + market_sizes | treatment_manager (YAML per-market) + token-level override |
| Role assignment | predefined_goals + RoleSlot + permanent_speculators | Goal stored in token, default 0 (speculator), configurable |
| Market limit | user_historical_markets + max_markets_per_human | Simple counter on session object |
| Concurrency | Shared dicts, race conditions | Each session independent, no shared state |

---

## Execution Plan

### Phase 0: Import safety (before deleting anything)

**Goal**: Remove all imports of modules we're about to delete, verify no runtime errors.

#### `back/traders/__init__.py`
- DELETE line 6: `from .simple_order_trader import SimpleOrderTrader`
- DELETE line 7: `from .spoofing_trader import SpoofingTrader`
- DELETE line 8: `from .manipulator_trader import ManipulatorTrader`
- DELETE line 9: `from .agentic_trader import AgenticBase, AgenticTrader, AgenticAdvisor`
- DELETE line 12: `LLMAdvisorTrader = AgenticTrader`

#### `back/core/trader_manager.py`
- DELETE imports: `ManipulatorTrader` (line 14), `SimpleOrderTrader` (line 16), `SpoofingTrader` (line 17), `AgenticTrader` (line 18), `AgenticAdvisor` (line 19)

#### `back/api/endpoints.py`
- DELETE 5 agentic endpoints (lines 149-198): `get_agentic_templates`, `get_agentic_prompts_yaml`, `update_agentic_prompts`, `get_agentic_template`, `update_agentic_template`
- DELETE agentic auto-enable logic (lines 1597-1599)

**Verify**: `python -c "from core.trader_manager import TraderManager"` — no ImportError.

---

### Phase 1: Safe deletions

**Goal**: Delete dead files, trim data_models, rewrite trader_manager.

#### 1A: Delete dead trader files
```
DELETE: back/traders/simple_order_trader.py
DELETE: back/traders/manipulator_trader.py
DELETE: back/traders/spoofing_trader.py
DELETE: back/traders/agentic_trader.py
DELETE: back/traders/rl/ (entire directory — ppo.py, fin_rl.py, ppo_env.py)
DELETE: back/reference/alessio/ (entire directory)
```

#### 1B: Delete config & test files
```
DELETE: back/config/agentic_prompts.yaml
DELETE: back/tests/test_agentic_trader.py
DELETE: back/tests/run_agentic_test.py
DELETE: back/tests/run_agentic_paper_test.py
```

#### 1C: Trim `back/core/data_models.py`

**14 fields to DELETE:**
| Field | Lines |
|-------|-------|
| `num_simple_order_traders` | 73-78 |
| `num_spoofing_traders` | 79-84 |
| `num_manipulator_traders` | 85-90 |
| `depth_book_shown` | 227-231 |
| `cancel_time` | 251-256 |
| `execution_throttle_ms` | 304-309 |
| `manipulator_open_shares` | 311-316 |
| `manipulator_open_time` | 317-322 |
| `manipulator_pause_time` | 323-328 |
| `manipulator_random_direction` | 329-333 |
| `num_agentic_traders` | 336-341 |
| `agentic_model` | 342-346 |
| `agentic_prompt_template` | 347-351 |
| `agentic_advisor_enabled` | 352-356 |

**4 TraderType enum values to DELETE:** `SIMPLE_ORDER` (47), `SPOOFING` (48), `MANIPULATOR` (49), `AGENTIC` (50)

**3 throttle dict entries to DELETE:** lines 365-367 (SIMPLE_ORDER, SPOOFING, AGENTIC)

#### 1D: Rewrite `back/core/trader_manager.py`

**DELETE methods** (not trim — full removal):
- `_create_simple_order_traders()` (lines 82-101)
- `_create_manipulator_traders()` (lines 129-141)
- `_create_spoofing_traders()` (lines 144-151)
- `_create_agentic_traders()` (lines 153-177)
- `_create_advisor_for_human()` (lines 210-238)

**REWRITE `__init__`**: Remove 5 bot creation calls (lines 49, 52-55), remove from traders dict (lines 63-65, 67).

**REWRITE `add_human_trader`**: Remove agentic advisor creation (lines 205-206).

**Result**: ~210 lines (from 317).

**Verify**: Platform starts, lab flow works with 3 traders.

---

### Phase 2: Admin auth

**Goal**: Simple password login so admin works without Firebase.

**Implementation** (~20 LOC in `back/api/auth.py`):
```python
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin')

async def get_current_admin_user(credentials = Depends(HTTPBearer())):
    if credentials.credentials != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Invalid admin token")
    return {"username": "admin", "is_admin": True}
```

Keep Firebase as transitional fallback until Phase 3b.

**9 admin endpoints** depend on this: `/admin/generate-lab-links`, `/admin/reset_state`, `/admin/treatment-overrides`, `/admin/download_*`, etc.

**Verify**: Admin can log in with password, generate lab links, access admin panel.

---

### Phase 3: Backend restructure

#### Phase 3a: Split `endpoints.py` (pure refactor, no logic change)

**47 endpoints → 7 route files:**

| File | Endpoints | Count |
|------|-----------|-------|
| `routes/auth.py` | `/user/login`, `/admin/login`, `/session/status`, `/session/reset-for-new-market` | 4 |
| `routes/trading.py` | `/trading/start`, `/trader_info/{id}`, `/trader/{id}/market`, `/traders/defaults`, `/market_metrics` | 6 |
| `routes/admin.py` | `/admin/update_base_settings`, `/admin/reset_state`, `/admin/generate-lab-links`, `/admin/treatment-overrides`, `/admin/run_headless_batch`, etc. | 17 |
| `routes/questionnaire.py` | `/save_questionnaire_response`, `/questionnaire/status`, `/consent/*`, `/save_premarket_interaction` | 5 |
| `routes/data.py` | `/files`, `/files/grouped`, `/files/{path}`, `/admin/download_*` | 5 |
| `routes/lab.py` | `/sessions`, `/sessions/{id}/force-start` | 3 |
| `routes/test.py` | `/api/test/*` | 7 |

**`endpoints.py` becomes router aggregator** (~50 LOC):
```python
app = FastAPI()
app.include_router(auth.router)
app.include_router(trading.router)
# ... etc
```

**Verify**: All endpoints still respond correctly.

#### Phase 3b: Rewrite session + auth (the hard part)

**Rewrite `session_manager.py`** — 852 LOC → ~150 LOC.

Minimum interface (called by `simple_market_handler.py`):
| Method | Purpose |
|--------|---------|
| `join_session(username, params)` | User joins, gets role/goal |
| `mark_user_ready(username)` | Check if market can start |
| `start_trading_session(username)` | Create TraderManager |
| `get_session_status(username)` | Current state |
| `remove_user_from_session(username)` | Cleanup |
| `cleanup_finished_markets()` | GC finished markets |
| `reset_all()` | Admin reset |

Treatment application flow (simplified):
```python
market_count = len(user_historical_markets[username])
params = treatment_manager.get_merged_params(market_count, base_params)
# Apply token-level override if present
if username in user_treatment_groups:
    tg = user_treatment_groups[username]
    if tg in treatment_overrides:
        params.update(treatment_overrides[tg])
```

**Rewrite `auth.py`** — Lab token + admin password only. Remove all Firebase/Prolific paths from `get_current_user()`.

**Verify**: Full experiment flow (generate links → onboard → trade → summary).

#### Phase 3c: Delete old modules

```
DELETE: back/api/prolific_auth.py (247 LOC)
DELETE: back/api/google_sheet_auth.py (94 LOC)
DELETE: back/utils/calculate_metrics.py (130 LOC) — functions exist in logfiles_analysis
DELETE: back/utils/websocket_utils.py (41 LOC) — inline sanitize_websocket_message()
```

Remove all dead imports from routes/ files.

---

### Phase 4: Frontend rewrite

**Follow `FRONTEND-DESIGN.md` for all visual design.**

#### 4a: Auth.vue rewrite

**DELETE** (~260 lines):
- Prolific credential form (lines 17-53)
- Google OAuth buttons (lines 55-94)
- Prolific state refs (lines 133-142)
- Turnstile CAPTCHA functions (lines 144-175)
- `getProlificParams()` (lines 177-204)
- `signInWithGoogle()` (lines 246-266)
- `adminSignInWithGoogle()` (lines 268-309)
- `handleProlificCredentialLogin()` (lines 311-337)

**NEW flow**:
1. Check URL for `LAB_TOKEN` → auto-login
2. No token → show admin password form
3. ~80 LOC total

#### 4b: Navigation.js slim-down (378 → ~258 LOC)

**KEEP**: `getRedirectForStatus`, `startTrading`, `onMarketStarted`, `onTradingEnded`, `startNextMarket`, `goToAdmin`, `logout`, `recoverSession`, `afterLogin`, `getRouteForStep`, `getStepForRoute`

**DELETE**: `loadUserProgress`, `saveUserProgress`, `afterProlificLogin`, `completeStudy`, `nextOnboardingStep`, `prevOnboardingStep`, `goToOnboardingStep`

#### 4c: Store simplification

**`store/app.js`** (793 LOC):
- DELETE 19 delegating getters (lines 66-91) — components import specialized stores directly
- DELETE AI Advisor state (lines 56-59)

**`store/auth.js`** (272 → ~80 LOC):
- KEEP: `labLogin()`, `logout()`, `isAuthenticated`, `isLabUser`
- DELETE: `prolificLogin()` (lines 68-135), `login()` Firebase (lines 174-219), `adminLogin()` (lines 221-230)
- ADD: `adminPasswordLogin(password)` (~20 LOC)

#### 4d: Delete dead components

| Component | Imported in | Action |
|-----------|------------|--------|
| `AIPromptsTab.vue` (286 LOC) | AdminDashboard.vue line 54 | DELETE + remove import/tab |
| `AIAdvisor.vue` (286 LOC) | TradingDashboard.vue line 205 | DELETE + remove import |
| `LogFilesManager.vue` (452 LOC) | AdminDashboard.vue line 56 | DELETE + remove sidebar |
| `OrderThrottling.vue` | **Not imported anywhere** | DELETE (dead code) |

#### 4e: ConfigTab.vue trim

- DELETE agentic template dropdown (lines 59-70)
- DELETE `loadAgenticTemplates()` function (lines 483-489)
- DELETE `agenticTemplates` ref (line 338)
- UPDATE `traderTypes` array: remove `'SIMPLE_ORDER'` (line 364)
- UPDATE `titleMap`: remove `'agentic_parameter'` and `'manipulator_parameter'` (lines 373-379)

#### 4f: Visual redesign

Rewrite all pages with fresh UI per FRONTEND-DESIGN.md. Onboarding content unchanged, look and feel redesigned. Trading dashboard, summary, admin — all get new visual treatment.

---

### Phase 5: Verification

1. Generate 4 lab links with 2 treatments
2. Open link 1, complete ALL onboarding pages, trade 2 markets
3. Verify summary shows correct metrics (not N/A)
4. Open link 3 (different treatment), verify different `informed_trade_intensity`
5. Check log files have `LAB_X` in filename
6. Admin can log in with password, download logs, view `parameter_history`
7. Test error paths: invalid lab token, expired token, mid-market page refresh
8. Test concurrent sessions: 2 users trading simultaneously in separate sessions
9. Verify no ImportError on startup (`python -c "import api.endpoints"`)

---

## Notes from Review

- **Role flexibility**: Keep `goal` as a configurable parameter (default 0 = speculator). Don't hardcode. Alessio may want informed human traders in future experiments.
- **market_sizes**: Keep as a vestigial field (unused in simple flow, costs nothing, preserves option for multi-user markets later).
- **trader_manager.py**: Full rewrite, not trim — 5 bot creation methods must be entirely removed.
- **Race condition**: With independent per-user sessions, the `cleanup_finished_markets()` race condition that crashed the April 1 experiment vanishes entirely.

## CI/CD Strategy

- All work stays on `refactor/core-rewrite` branch
- Do NOT merge to main until Phase 5 verification passes
- Docker/deployment files update as needed in Phase 3
- Consider disabling auto-deploy during merge window

## Files Not Changed (kept as-is)
- `core/trading_platform.py`, `core/handlers.py`, `core/services.py`
- `core/orderbook_manager.py`, `core/events.py`, `core/transaction_manager.py`
- `traders/base_trader.py`, `traders/informed_trader.py`, `traders/noise_trader.py`
- `traders/human_trader.py`, `traders/book_initializer.py`
- `utils/logfiles_analysis.py`, `core/parameter_logger.py`
- All onboarding page content (pages 0-8)
- `TradingDashboard.vue`, `PlaceOrder.vue`, `MarketSummary.vue`, `PriceHistory.vue`
