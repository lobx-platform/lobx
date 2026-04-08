# Audit 05 -- Vue 3 Component Architecture

**Date:** 2026-04-08
**Branch:** `refactor/core-rewrite`
**Scope:** Component tree, file structure, data flow, modern Vue 3 patterns

---

## 1. Current Structure Analysis

### File tree (21 `.vue` files total)

```
front/src/
  App.vue                              (45 LOC)  -- root shell, global snackbar
  components/
    Auth.vue                           (381 LOC) -- login page
    UserLanding.vue                    (406 LOC) -- onboarding wizard wrapper
    TradingDashboard.vue               (831 LOC) -- main trading page  <-- PROBLEM
    pages/
      0.vue  (consent)                 (676 LOC)
      1.vue  (welcome)                 (112 LOC)
      2.vue  (platform)               (321 LOC)
      3.vue  (setup)                   (237 LOC)
      4.vue  (earnings)               (501 LOC)
      6.vue  (participants)           (140 LOC)
      7.vue  (questions)              (356 LOC)
      8.vue  (ready)                  (297 LOC)
    trading/
      PlaceOrder.vue                   (484 LOC)
      OrderHistory.vue                 (338 LOC)
      ActiveOrders.vue                 (325 LOC)
      MarketMessages.vue               (206 LOC)
    charts/
      BidAskDistribution.vue           (154 LOC)
      PriceHistory.vue                 (182 LOC)
    market/
      MarketSummary.vue                (585 LOC)
      AdminDashboard.vue               (352 LOC)
      admin/
        ConfigTab.vue
        MarketsTab.vue
```

### Observations

| Aspect | Status | Notes |
|--------|--------|-------|
| Flat vs nested | **Mixed** | `trading/` and `charts/` are properly nested; `pages/` uses numeric filenames; top-level `components/` still holds 3 "page" components directly |
| Page vs feature separation | **Weak** | No `views/` or `pages/` distinction -- page-level components and feature components live together |
| Naming convention | **Inconsistent** | `0.vue` through `8.vue` give no hint of content; `TradingDashboard.vue` sits at top level alongside `Auth.vue` |
| Composables | **Minimal** | Only `composables/utils.js` exists (a single `formatNumber` helper) |
| Store architecture | **Fragmented** | 5 stores (`app`, `auth`, `market`, `session`, `websocket`, `ui`) with `app.js` at 576 LOC acting as a god-store |

### Route structure

The router correctly uses lazy-loading (`() => import(...)`) for all routes. Onboarding is nested under `/onboarding` with named child routes. Legacy routes redirect properly. This is well-designed.

---

## 2. TradingDashboard.vue -- 831 LOC Decomposition

This is the single largest component and the most critical to refactor. It mixes three distinct concerns:

### Current responsibilities (all in one file)

1. **Header bar** -- role chip, PnL/shares/cash stats, goal progress, countdown timer (~100 lines template, ~200 lines script)
2. **Waiting room** -- "Waiting for Traders" screen with join count (~30 lines)
3. **Trading grid** -- 3x2 card layout composing 6 child components (~60 lines)
4. **Goal/role logic** -- 15+ computed properties for goal state, role display, progress (~150 lines)
5. **Lifecycle orchestration** -- trader init, WebSocket reconnect, market timeout, zoom hack (~80 lines)
6. **DOM hacks** -- manual `document.body.style.zoom`, `querySelector` for header height (~30 lines)

### Recommended decomposition

```
components/trading/
  TradingDashboard.vue        -- slim orchestrator (<150 LOC)
  TradingHeader.vue           -- header bar with stats, role, timer
  TradingWaitingRoom.vue      -- pre-market waiting screen
  TradingGrid.vue             -- 3x2 card layout (optional, or keep inline)

composables/
  useGoalTracking.ts          -- goal, goalProgress, isGoalAchieved, goalType, etc.
  useRoleDisplay.ts           -- roleDisplay, roleColor, roleIcon
  useMarketCountdown.ts       -- remainingTime watcher, market timeout logic
  useTradingInit.ts           -- trader initialization, WebSocket connection
```

**Why this matters:** The current file has two `onMounted` hooks (lines 281 and 524) because logic was bolted on over time. Goal-related computed properties account for ~150 lines that are pure derivations from `traderAttributes` -- a textbook composable extraction.

### Specific code smells

- **`document.body.style.zoom = '0.95'`** (line 283): A global side effect buried in a component. Should be a CSS transform on `.trading-dashboard` or a Vuetify layout config.
- **Manual header height measurement** (lines 525-550): Nested `onMounted` inside `onMounted` with `setTimeout`. Replace with CSS `position: sticky` or Vuetify's built-in app bar height handling.
- **Debug computed** (`debugDisplayValues`, line 257): Dead code that creates a reactive object nobody reads.
- **Empty `onUnmounted`** (lines 308-310): No-op lifecycle hook.

---

## 3. Onboarding Pages: `0.vue` through `8.vue`

### Current pattern

8 separate files (numbered, not named) rendered as nested `<router-view>` children inside `UserLanding.vue`. Each page receives `traderAttributes` and `iconColor` as props and emits `update:canProgress`.

### Assessment: The current pattern is correct, but the naming is wrong

**Keep separate files.** Each onboarding page has genuinely different content:
- `0.vue` (consent) = 676 LOC with a legal form and checkbox
- `7.vue` (questions) = 356 LOC with a quiz engine
- `8.vue` (ready) = 297 LOC with a market-join flow

A single component with steps/slots would be worse: it would become a 2500+ LOC monster, and the individual pages have no shared template logic. The `UserLanding.vue` wizard wrapper already handles shared concerns (progress bar, navigation, step tracking).

**What to fix:**

| Issue | Fix |
|-------|-----|
| Numeric filenames (`0.vue`, `1.vue`) | Rename to `ConsentPage.vue`, `WelcomePage.vue`, `PlatformPage.vue`, etc. |
| Missing page `5.vue` | File `6.vue` maps to step 5 in the router -- confusing. Renumber or (better) name by content |
| Large pages | `0.vue` (676 LOC) and `4.vue` (501 LOC) could extract shared styled sections into reusable `<InfoCard>` or `<ConsentSection>` sub-components |
| Props drilling | `traderAttributes` is passed from `UserLanding` -> page. Most pages don't use it. Only pass what each page needs, or use `provide/inject` |

---

## 4. Store Communication Patterns

### Current state: three patterns co-existing

| Pattern | Where used | Problem |
|---------|------------|---------|
| **Direct store access** | `PlaceOrder.vue` calls `useTraderStore()` and `useMarketStore()` directly | Components are tightly coupled to store shape |
| **Props down** | `TradingDashboard` passes `isGoalAchieved` and `goalType` to all 6 children | Good practice, but these are derived from the store anyway -- children could compute them |
| **Events up** | Onboarding pages emit `update:canProgress` to `UserLanding` | Correct use of events for parent-owned state |

### Recommendation: Standardize on "stores for global state, composables for derived logic"

```
                        Pinia stores
                  (app, market, session, auth, ws)
                            |
                     composables layer
              (useGoalTracking, useTraderRole, ...)
                            |
                      page components
              (TradingDashboard, MarketSummary)
                            |
                    feature components
              (PlaceOrder, OrderHistory, ...)
```

**Rules:**
1. **Feature components** (PlaceOrder, ActiveOrders, charts) should receive data via **props** from their parent page, not reach into stores directly. This makes them testable and reusable.
2. **Composables** should encapsulate store reads + derived computations. Example: `useGoalTracking()` wraps `traderStore.traderAttributes` and exposes `goal`, `goalProgress`, `isGoalAchieved`, `goalType`, `goalProgressPercentage` -- all the computed properties currently duplicated/scattered.
3. **Page components** (TradingDashboard, MarketSummary) are the "smart" layer that calls composables and passes results as props.
4. **`provide/inject`** should be used for deeply-nested cases only (e.g., if TradingDashboard -> TradingGrid -> PlaceOrder needs `isGoalAchieved` without prop drilling through an intermediate wrapper).

### Specific fix: `PlaceOrder.vue` store coupling

Currently PlaceOrder directly calls `useTraderStore()`, `useMarketStore()`, and `useUIStore()`. It reads `bidData`, `askData`, `gameParams`, `trader`, and `extraParams`. It also calls `tradingStore.addOrder()` directly.

Better approach:
```vue
// PlaceOrder.vue -- receives everything via props
const props = defineProps<{
  buyPrices: number[]
  sellPrices: number[]
  availableCash: number
  availableShares: number
  isGoalAchieved: boolean
  goalType: 'buy' | 'sell' | 'free'
  isPaused: boolean
}>()

const emit = defineEmits<{
  placeOrder: [type: string, price: number]
}>()
```

This makes PlaceOrder a pure presentation component that can be tested without any store mocking.

---

## 5. Modern Vue 3 Patterns to Adopt

### 5a. Composables for shared logic

**Current:** Only one composable exists (`utils.js` with `formatNumber`). All business logic lives in components or the god-store (`app.js`, 576 LOC).

**Target composables to extract:**

| Composable | Source | What it encapsulates |
|------------|--------|---------------------|
| `useGoalTracking` | TradingDashboard lines 313-469 | goal, goalProgress, isGoalAchieved, goalType, goalProgressPercentage, goalProgressColor, cancelAllActiveOrders on goal achieved |
| `useRoleDisplay` | TradingDashboard lines 394-430 | roleDisplay, roleColor, roleIcon -- reactive to traderAttributes.goal |
| `useMarketCountdown` | TradingDashboard lines 272-276, 433-448 | remainingTime watcher, market timeout interval, finalizingDay trigger |
| `useTradingInit` | TradingDashboard lines 281-306, 519-550 | trader initialization, WebSocket reconnection, header height adjustment |
| `useOrderPricing` | PlaceOrder lines 122-158 | buyPrices, sellPrices derivation from bid/ask data and step |
| `usePauseState` | PlaceOrder lines 182-220 | isHumanTraderPaused, isPausingSystemActive |
| `useFormatters` | Expand existing utils.js | formatNumber, formatPrice, formatValue (currently duplicated in MarketSummary and PlaceOrder) |

### 5b. `provide/inject` for deep prop passing

The `isGoalAchieved` and `goalType` props are passed from TradingDashboard to all 6 child components identically. This is a candidate for `provide/inject`:

```js
// TradingDashboard.vue (or a composable)
provide('goalState', {
  isGoalAchieved,
  goalType,
})

// Any child component
const { isGoalAchieved, goalType } = inject('goalState')
```

This eliminates 12 prop bindings (6 components x 2 props each) from the template.

### 5c. `defineModel` for two-way binding

The onboarding pages use `@update:canProgress="handleProgress"` which is a manual v-model pattern. With `defineModel`:

```vue
// In page component (e.g., 7.vue)
const canProgress = defineModel('canProgress', { type: Boolean, default: false })
// Directly set: canProgress.value = true

// In UserLanding.vue
<router-view v-model:canProgress="canProgressFromQuestions" />
```

### 5d. TypeScript adoption

The codebase uses plain JavaScript. Adding TypeScript (even incrementally, file by file) would:
- Make store shapes explicit and catch mismatches at build time
- Document props contracts (currently, `traderAttributes` shape is implicit)
- Enable IDE auto-completion across the codebase

This is a low-priority, high-payoff investment that can be done file-by-file using `<script setup lang="ts">`.

---

## 6. Recommended Component Tree and File Structure

### Proposed directory layout

```
front/src/
  App.vue

  views/                               # Page-level "smart" components (1 per route)
    AuthPage.vue                        # was components/Auth.vue
    TradingPage.vue                     # was components/TradingDashboard.vue (slim)
    MarketSummaryPage.vue               # was components/market/MarketSummary.vue
    AdminPage.vue                       # was components/market/AdminDashboard.vue

  components/
    onboarding/                         # was pages/
      OnboardingLayout.vue              # was UserLanding.vue
      ConsentPage.vue                   # was 0.vue
      WelcomePage.vue                   # was 1.vue
      PlatformPage.vue                  # was 2.vue
      SetupPage.vue                     # was 3.vue
      EarningsPage.vue                  # was 4.vue
      ParticipantsPage.vue              # was 6.vue
      QuestionsPage.vue                 # was 7.vue
      ReadyPage.vue                     # was 8.vue
    trading/                            # Feature components (presentation-only)
      TradingHeader.vue                 # NEW: extracted from TradingDashboard
      TradingWaitingRoom.vue            # NEW: extracted from TradingDashboard
      PlaceOrder.vue
      OrderHistory.vue
      ActiveOrders.vue
      MarketMessages.vue
    charts/
      BidAskDistribution.vue
      PriceHistory.vue
    admin/
      ConfigTab.vue
      MarketsTab.vue
    shared/                             # Reusable UI primitives
      StatChip.vue                      # NEW: the stat-chip pattern repeated in header
      InfoCard.vue                      # NEW: metric-card pattern in MarketSummary

  composables/
    useGoalTracking.ts
    useRoleDisplay.ts
    useMarketCountdown.ts
    useTradingInit.ts
    useOrderPricing.ts
    usePauseState.ts
    useFormatters.ts                    # expand existing utils.js

  stores/                               # rename store/ -> stores/ (Vue convention)
    trader.ts                           # rename app.js, split god-store
    market.ts
    session.ts
    auth.ts
    websocket.ts
    ui.ts

  services/
    navigation.js
    api/                                # axios instance + typed API calls
      axios.js
```

### Key structural changes

1. **Separate `views/` from `components/`** -- Views are route-level smart components that compose features. Components are reusable UI units. This is the standard Vue convention (used by Vue CLI scaffolding, Nuxt, and most enterprise codebases).

2. **Rename onboarding pages** -- `0.vue` -> `ConsentPage.vue`, etc. Named files are self-documenting and allow grep/search to work.

3. **Extract `TradingHeader.vue`** -- The header bar alone is ~200 lines of template+style. It has its own distinct visual identity and could be developed independently.

4. **Create a `shared/` folder** -- The `stat-chip` pattern (icon + label + mono value) appears 4 times in TradingDashboard and could appear in MarketSummary too. A `StatChip.vue` component eliminates ~40 lines of repeated markup.

5. **Split the god-store** -- `app.js` (576 LOC) handles trader state, order management, game params, market participants, session status, and message routing. At minimum, extract order management into `stores/orders.ts`.

---

## Priority Order for Refactoring

| Priority | Task | Impact | Effort |
|----------|------|--------|--------|
| **P0** | Rename `pages/0.vue`-`8.vue` to descriptive names | Developer experience | 30 min |
| **P1** | Extract `useGoalTracking` composable | Removes ~150 LOC from TradingDashboard | 1 hr |
| **P1** | Extract `TradingHeader.vue` | Reduces TradingDashboard to ~400 LOC | 1 hr |
| **P2** | Extract `TradingWaitingRoom.vue` | Clean separation of pre/post-start states | 30 min |
| **P2** | Extract `useRoleDisplay` + `useMarketCountdown` composables | Completes TradingDashboard cleanup | 1 hr |
| **P2** | Make PlaceOrder prop-driven (remove direct store access) | Testability, reusability | 2 hr |
| **P3** | Move page components to `views/` folder | Conventional structure | 1 hr |
| **P3** | Remove DOM hacks (zoom, manual header height) | Eliminates fragile imperative code | 1 hr |
| **P4** | Introduce TypeScript incrementally | Long-term maintainability | Ongoing |

---

## References

- [Vue 3 + TypeScript Best Practices: 2025 Enterprise Architecture Guide](https://eastondev.com/blog/en/posts/dev/20251124-vue3-typescript-best-practices/)
- [How to Structure a Large Scale Vue.js Application -- Vue School](https://vueschool.io/articles/vuejs-tutorials/how-to-structure-a-large-scale-vue-js-application/)
- [Vue Best Practices in 2026 -- OneHorizon](https://onehorizon.ai/blog/vue-best-practices-in-2026-architecting-for-speed-scale-and-sanity)
- [Mastering Vue Components Folder Structure -- Vue School](https://vueschool.io/articles/vuejs-tutorials/structuring-vue-components/)
- [Good practices and Design Patterns for Vue Composables -- DEV Community](https://dev.to/jacobandrewsky/good-practices-and-design-patterns-for-vue-composables-24lk)
- [Composables -- Vue.js Official Docs](https://vuejs.org/guide/reusability/composables.html)
- [Feature-Sliced Design for Vue](https://feature-sliced.design/blog/vue-application-architecture)
