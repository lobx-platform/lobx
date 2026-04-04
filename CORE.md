# LOBX Platform — Core Rewrite Plan

## Why

The platform grew organically to serve Prolific, Firebase, lab tokens, 8 bot types, agentic LLM traders, and complex cohort/treatment logic. After running actual experiments, we know what's needed. The rest is dead weight that causes bugs.

**The real problem**: `session_manager.py` (852 LOC) is incomprehensible. Cohorts, treatment groups, market_sizes, permanent_roles, historical_markets — nobody can trace the flow. This caused every major bug in the April 1 experiment.

**Current**: ~13,700 LOC backend, ~8,900 LOC frontend.
**Target**: Cut 40-50%. Make the experiment flow obvious to anyone reading the code.

## Principles

1. **Lab-first** — Lab token is the only user auth. Admin gets a simple password login (not Firebase OAuth).
2. **Three traders only** — Human + Informed + Noise. Everything else is deleted.
3. **Obvious experiment flow** — One user → one session → N markets. No cohort system. No market_sizes. No permanent_roles.
4. **One file, one job** — No file over 300 lines.
5. **Delete, don't comment** — If it's not needed, it's gone.

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
10+ dicts, 15+ methods, race conditions everywhere.

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
One user object, one loop, zero cohort logic.

### What changes
| Concept | Before | After |
|---------|--------|-------|
| Session | Cohort-based, multi-user | One user = one session |
| Treatment | cohort_treatment_overrides + treatment_manager + market_sizes | Treatment params embedded in lab token or simple per-market config |
| Role assignment | predefined_goals + RoleSlot + permanent_speculators | Always speculator (goal=0). Fixed at token generation. |
| Market limit | user_historical_markets + max_markets_per_human | Simple counter on the session object |
| Concurrency | Shared dicts, race conditions | Each session is independent, no shared state |

## What to Keep

### Backend
| Module | Status | Notes |
|--------|--------|-------|
| `core/trading_platform.py` | **Keep** | Market orchestrator |
| `core/handlers.py` | **Keep** | Event-driven order handling |
| `core/services.py` | **Keep** | Order/transaction services |
| `core/orderbook_manager.py` | **Keep** | Price-time matching |
| `core/events.py` | **Keep** | Event dataclasses |
| `core/transaction_manager.py` | **Keep** | Transaction tracking |
| `core/simple_market_handler.py` | **Rewrite** | Simplify to direct session management |
| `core/data_models.py` | **Trim** | Remove 13 unused fields, 4 enum values |
| `core/session_manager.py` | **Rewrite** | Replace 852 LOC with ~150 LOC simple session |
| `core/trader_manager.py` | **Trim** | Remove 5 bot type branches |
| `core/treatment_manager.py` | **Keep** | YAML per-market treatments |
| `core/parameter_logger.py` | **Keep** | Audit trail |
| `traders/base_trader.py` | **Keep** | Abstract base |
| `traders/human_trader.py` | **Keep** | WebSocket human |
| `traders/informed_trader.py` | **Keep** | Core experiment bot |
| `traders/noise_trader.py` | **Keep** | Core experiment bot |
| `traders/book_initializer.py` | **Keep** | Initial order book |
| `api/lab_auth.py` | **Keep** | Token generation/validation |
| `api/auth.py` | **Rewrite** | Lab token + admin password only |
| `utils/logfiles_analysis.py` | **Keep** | Post-experiment metrics |
| `utils/utils.py` | **Keep** | Logger setup |

### Frontend
| Module | Status | Notes |
|--------|--------|-------|
| Onboarding pages (0-8) | **Keep content** | Same pages, same content. Code cleanup only. |
| `TradingDashboard.vue` | **Keep** | Main trading view |
| `PlaceOrder.vue` | **Keep** | Order entry |
| `MarketSummary.vue` | **Keep** | Post-market results + questionnaire |
| `PriceHistory.vue` | **Keep** | Price chart |
| `Auth.vue` | **Rewrite** | Lab-token-only + admin password |
| `AdminDashboard.vue` | **Trim** | Remove AI/agentic tabs |
| `ConfigTab.vue` | **Trim** | Remove agentic config, dead trader type UI |
| `services/navigation.js` | **Slim down** | Keep market lifecycle funcs, delete onboarding over-engineering |
| `store/app.js` | **Rewrite** | Kill 19 delegating getters |
| `store/auth.js` | **Rewrite** | Lab-only + admin password, ~80 lines |

## What to Delete

### Backend (~3,500 LOC)
- `traders/agentic_trader.py` (844) + 6 API endpoints + AIPromptsTab references
- `traders/manipulator_trader.py` (125)
- `traders/spoofing_trader.py` (190)
- `traders/simple_order_trader.py` (47)
- `traders/rl/` directory (404)
- `reference/alessio/` directory (240)
- `api/prolific_auth.py` (247)
- `api/google_sheet_auth.py` (94)
- `utils/calculate_metrics.py` (130) — duplicates logfiles_analysis
- `utils/websocket_utils.py` (41) — inline the one function
- `config/agentic_prompts.yaml`
- All agentic/advisor/prolific code paths in endpoints.py
- Tests: `test_agentic_trader.py`, `run_agentic_test.py`, `run_agentic_paper_test.py`

### Frontend (~2,000 LOC)
- `components/market/admin/AIPromptsTab.vue` (286)
- `components/market/AIAdvisor.vue` (286)
- `components/market/LogFilesManager.vue` (452)
- `components/market/OrderThrottling.vue`
- Firebase OAuth flow in Auth.vue
- Prolific credential flow in Auth.vue
- `firebaseConfig.js` (replace with minimal config if needed for hosting only)

### data_models.py — Fields to Delete
```
num_simple_order_traders, num_spoofing_traders, num_manipulator_traders,
manipulator_open_shares, manipulator_open_time, manipulator_pause_time,
manipulator_random_direction, num_agentic_traders, agentic_model,
agentic_prompt_template, agentic_advisor_enabled,
execution_throttle_ms, depth_book_shown, cancel_time
```

### data_models.py — TraderType Enum Cleanup
Delete: `SIMPLE_ORDER`, `SPOOFING`, `MANIPULATOR`, `AGENTIC`
Keep: `NOISE`, `MARKET_MAKER`, `INFORMED`, `HUMAN`, `INITIAL_ORDER_BOOK`

## Execution Order

### Phase 0: Import safety (before deleting anything)
1. Grep all imports of modules to be deleted
2. Update `traders/__init__.py`, `trader_manager.py`, `endpoints.py`, `auth.py` to remove dead imports
3. Verify no runtime ImportError after removing imports (but before deleting files)

### Phase 1: Safe deletions (zero risk)
4. Delete dead trader files (RL, reference, manipulator, spoofing, simple_order, agentic)
5. Delete `config/agentic_prompts.yaml`
6. Delete agentic test files (`test_agentic_trader.py`, `run_agentic_test.py`, `run_agentic_paper_test.py`)
7. Trim `data_models.py` (13 fields, 4 enum values)
8. **Rewrite `trader_manager.py`** — remove 5 bot creation methods entirely (not just trim)
9. Test: platform starts, existing lab flow still works with 3 traders

### Phase 2: Admin auth (unblock everything else)
10. Add admin password login: env var `ADMIN_PASSWORD`, Bearer token, ~20 LOC
11. Update `get_current_admin_user()` to accept admin password OR Firebase (transitional)
12. Test: admin can log in and generate lab links

### Phase 3: Backend restructure (split into sub-steps, test between each)
**3a: Split endpoints.py** (pure refactor, no logic change)
13. Extract → `routes/{auth, trading, admin, questionnaire}.py`
14. Test: all existing endpoints still work

**3b: Rewrite session + auth** (the hard part)
15. **Rewrite `session_manager.py`** — replace cohort system with simple per-user session
16. Rewrite `auth.py` — lab token + admin password only, remove Firebase/Prolific paths
17. Test: full experiment flow works (generate links → onboard → trade → summary)

**3c: Delete old modules** (cleanup)
18. Delete `prolific_auth.py`, `google_sheet_auth.py`
19. Delete agentic endpoints from routes
20. Inline `websocket_utils.py`, delete `calculate_metrics.py`

### Phase 4: Frontend rewrite
**Follow `FRONTEND-DESIGN.md` for all visual design decisions.**

21. Rewrite `Auth.vue` — lab token auto-login + admin password form
22. Slim down `navigation.js`:
    - **Keep**: `startTrading`, `onMarketStarted`, `onTradingEnded`, `startNextMarket`, `afterLogin`, `logout`, `recoverSession`
    - **Delete**: `loadUserProgress`, `saveUserProgress`, `afterProlificLogin`, `completeStudy`, step navigation functions
23. Trim `ConfigTab.vue` — remove agentic/deleted trader config, update traderTypes array
24. Delete `AIPromptsTab.vue`, `AIAdvisor.vue`, `LogFilesManager.vue`
25. Simplify stores: flatten `app.js` (kill 19 delegating getters), rewrite `auth.js` to lab-only (~80 LOC)
26. Remove Firebase OAuth and Prolific flows from all frontend code
27. **Rewrite UI**: all pages get fresh visual design per FRONTEND-DESIGN.md. Onboarding content stays the same, look and feel changes.

### Phase 5: Verification
28. Generate 4 lab links with 2 treatments
29. Open link 1, complete ALL onboarding pages, trade 2 markets
30. Verify summary shows correct metrics (not N/A)
31. Open link 3 (different treatment), verify different informed_trade_intensity
32. Check log files have LAB_X in filename
33. Admin can log in with password, download logs, view parameter_history
34. Test error paths: invalid lab token, expired token, mid-market page refresh
35. Test concurrent sessions: 2 users trading simultaneously in separate sessions

## CI/CD Strategy

- All work stays on `refactor/core-rewrite` branch
- Do NOT merge to main until Phase 5 verification passes
- Consider disabling auto-deploy during merge window
- Docker/deployment files (`docker-compose.yml`, `Dockerfile.back`, CI workflow) update as needed in Phase 3

## Frontend Design

All frontend pages will be rewritten with a fresh visual identity. See `FRONTEND-DESIGN.md` for the design system and aesthetic guidelines. Onboarding **content** (consent text, instructions, questions) stays unchanged; the **look and feel** is redesigned.

## Notes from Review

- **Role flexibility**: Keep `goal` as a configurable parameter (default 0 = speculator). Don't hardcode. Alessio may want informed human traders in future experiments.
- **market_sizes**: Keep as a vestigial field (unused in simple flow, but costs nothing and preserves option for multi-user markets later).
- **trader_manager.py**: Mark as "Rewrite" not "Trim" — 5 bot creation methods must be fully removed, not just commented out.

## Files Not Changed (kept as-is)
- `core/trading_platform.py`, `core/handlers.py`, `core/services.py`
- `core/orderbook_manager.py`, `core/events.py`, `core/transaction_manager.py`
- `traders/base_trader.py`, `traders/informed_trader.py`, `traders/noise_trader.py`
- `traders/human_trader.py`, `traders/book_initializer.py`
- `utils/logfiles_analysis.py`, `core/parameter_logger.py`
- All onboarding page content (pages 0-8)
- `TradingDashboard.vue`, `PlaceOrder.vue`, `MarketSummary.vue`, `PriceHistory.vue`
