# LOBX Platform — Core Rewrite Plan

## Why

The platform grew organically to serve multiple auth flows (Firebase, Prolific, Lab), multiple trader types (8 bot types), and multiple experiment paradigms. After running actual lab experiments, we know exactly what's needed and what's dead weight.

**Current state**: ~13,700 LOC backend, ~8,900 LOC frontend. `endpoints.py` alone is 2,058 lines.

**Target**: Cut codebase by 40-50%. Fewer bugs, faster iteration, easier onboarding for new team members.

## Principles

1. **Lab-first** — Lab token auth is the only auth. Remove Firebase OAuth and Prolific credential flows entirely.
2. **Three traders only** — Human + Informed + Noise. Delete manipulator, spoofing, agentic, simple_order, RL/PPO.
3. **One file, one job** — No file over 300 lines. Split `endpoints.py` and `session_manager.py`.
4. **Delete, don't comment** — No `# TODO: remove later`. If it's not needed, it's gone.
5. **Frontend follows backend** — Simplify stores, kill NavigationService, flatten onboarding.

## What to Keep

### Backend
| Module | Status | Notes |
|--------|--------|-------|
| `core/trading_platform.py` | **Keep** | Market orchestrator, clean |
| `core/handlers.py` | **Keep** | Event-driven order handling |
| `core/services.py` | **Keep** | Order/transaction service layer |
| `core/orderbook_manager.py` | **Keep** | Simple price-time matching, perfect for lab |
| `core/events.py` | **Keep** | Event classes |
| `core/data_models.py` | **Trim** | Remove unused fields (manipulator_*, spoofing_*, agentic_*, 30+ fields) |
| `core/session_manager.py` | **Split** | → `session.py` (join/ready/start) + `cleanup.py` |
| `core/trader_manager.py` | **Trim** | Remove 5 bot type branches |
| `core/treatment_manager.py` | **Keep** | YAML treatments still used for market sequence |
| `traders/base_trader.py` | **Keep** | Abstract base |
| `traders/human_trader.py` | **Keep** | WebSocket human |
| `traders/informed_trader.py` | **Keep** | Core experiment bot |
| `traders/noise_trader.py` | **Keep** | Core experiment bot |
| `traders/book_initializer.py` | **Keep** | Initial order book seeding |
| `api/lab_auth.py` | **Keep** | Lab token generation/validation |
| `utils/logfiles_analysis.py` | **Keep** | Post-experiment metrics |
| `utils/utils.py` | **Keep** | Logger setup |

### Frontend
| Module | Status | Notes |
|--------|--------|-------|
| `TradingDashboard.vue` | **Keep** | Main trading view |
| `PlaceOrder.vue` | **Keep** | Order entry |
| `MarketSummary.vue` | **Keep** | Post-market results |
| `PriceHistory.vue` | **Keep** | Price chart |
| `Auth.vue` | **Rewrite** | Lab-token-only login, 50 lines max |
| `AdminDashboard.vue` | **Trim** | Remove AI/agentic tabs |
| `ConfigTab.vue` | **Trim** | Remove throttling UI, agentic config |
| Onboarding pages (0-8) | **Consolidate** | 8 pages → 3: Consent, Instructions, Ready |
| `store/app.js` | **Rewrite** | Kill 19 delegating getters, flatten |
| `store/auth.js` | **Rewrite** | Lab-only, 50 lines |
| `services/navigation.js` | **Delete** | Merge essential logic into router guards |

## What to Delete

### Backend (~3,000 LOC)
- `traders/agentic_trader.py` (844 LOC)
- `traders/manipulator_trader.py` (125 LOC)
- `traders/spoofing_trader.py` (190 LOC)
- `traders/simple_order_trader.py` (47 LOC)
- `traders/rl/` directory (404 LOC)
- `reference/alessio/` directory (240 LOC)
- `api/prolific_auth.py` (247 LOC)
- `api/google_sheet_auth.py` (94 LOC)
- `utils/calculate_metrics.py` (130 LOC) — duplicates logfiles_analysis
- `utils/websocket_utils.py` (41 LOC) — inline the one function
- All agentic/advisor code paths in endpoints.py, trader_manager.py

### Frontend (~3,000 LOC)
- `services/navigation.js` (377 LOC)
- `components/market/admin/AIPromptsTab.vue` (286 LOC)
- `components/market/AIAdvisor.vue` (286 LOC)
- `components/market/LogFilesManager.vue` (452 LOC)
- `components/market/OrderThrottling.vue`
- `components/market/BidAskDistribution.vue`
- Onboarding pages 1-4, 6 (merge into fewer pages)
- Firebase config and OAuth flow
- Prolific auth flow in Auth.vue

## Backend File Structure (After Rewrite)

```
back/
  api/
    routes/
      auth.py          # Lab token login, admin login (~100 LOC)
      trading.py       # /trading/start, WebSocket, trader_info (~200 LOC)
      admin.py         # Settings, generate-lab-links, downloads (~200 LOC)
      questionnaire.py # Save/load questionnaire responses (~100 LOC)
    lab_auth.py        # Token generation/validation
  core/
    market.py          # TradingPlatform (was trading_platform.py)
    orderbook.py       # OrderBookManager
    handlers.py        # Event handlers
    services.py        # Order/transaction services
    events.py          # Event dataclasses
    models.py          # TradingParameters (trimmed)
    session.py         # Session join/ready/start
    treatments.py      # Treatment config
  traders/
    base.py
    human.py
    informed.py
    noise.py
    book_init.py
  utils/
    logger.py
    metrics.py         # Merged logfiles_analysis + calculate_metrics
```

## Execution Order

1. **Delete dead code** — RL, reference, unused traders. Zero risk.
2. **Split endpoints.py** — Extract into routes/. Pure refactor, no logic change.
3. **Trim data_models.py** — Remove 30+ unused fields.
4. **Delete Prolific/Firebase auth** — Lab-only.
5. **Frontend: kill NavigationService** — Inline into guards.
6. **Frontend: consolidate onboarding** — 8 pages → 3.
7. **Frontend: simplify stores** — Flatten app.js, rewrite auth.js.
8. **Test end-to-end** — Generate lab links, run through full experiment flow.

## Verification

After each step, run:
1. Generate 4 lab links with 2 treatments on admin panel
2. Open link 1, complete onboarding, trade 2 markets, verify summary shows correct metrics
3. Open link 3 (different treatment), verify different informed_trade_intensity
4. Check log files have LAB_X in filename
