# Audit 07 — Frontend Stack Evaluation

**Date**: 2026-04-08
**Scope**: Framework, component library, build tooling, charting libraries, real-time infrastructure
**Perspective**: Blind code review — no project history context

---

## 1. Current Stack Inventory

| Layer | Library | Version (package.json) | Latest Stable (Apr 2026) | Status |
|-------|---------|----------------------|--------------------------|--------|
| Framework | Vue 3 | ^3.5.17 | 3.5.x (3.6 in beta) | Current |
| Component Library | Vuetify 3 | ^3.4.0 | ~3.8.x | **1-2 minor versions behind** |
| State Management | Pinia | ^3.0.3 | 3.x | Current |
| Persistence | pinia-plugin-persistedstate | ^4.7.1 | 4.x | Current |
| Router | vue-router | ^4.5.1 | 4.5.x | Current |
| Build Tool | Vite | ^7.0.0 | 8.x (Vite 8 shipped Mar 2026) | **One major behind** |
| Vite Plugin | @vitejs/plugin-vue | ^6.0.0 | 6.x | Current |
| Vuetify Plugin | vite-plugin-vuetify | ^2.1.1 | 2.x | Current |
| WebSocket | socket.io-client | ^4.8.3 | 4.x | Current |
| HTTP | axios | ^1.6.5 | ~1.8.x | Slightly behind but fine |
| Icons (MDI) | @mdi/font | ^7.0.96 | 7.x | Current |
| Icons (Lucide) | lucide-vue-next | ^0.523.0 | 0.5xx | Current |
| Animation | @vueuse/motion | ^3.0.3 | 3.x | Current |
| Charting (1) | chart.js | ^4.5.0 | 4.x | Current |
| Charting (2) | highcharts + highcharts-vue | ^12.3.0 / ^2.0.1 | 12.x | Current |
| Charting (3) | apexcharts + vue3-apexcharts | ^4.7.0 / ^1.8.0 | 4.x | Current |
| Auth/Backend | firebase | ^11.9.1 | 11.x | Current |
| Toast | vue-sonner | ^2.0.1 | 2.x | Current |
| Events | mitt | ^3.0.1 | 3.x | Current |
| Utilities | lodash | ^4.17.21 | 4.17.21 | Current (unchanged for years) |
| CSS | sass | ^1.89.2 | 1.8x | Current |

### Summary
The core stack (Vue, Pinia, vue-router) is current. The two notable gaps are:
- **Vite 7** is one major version behind (Vite 8 shipped March 2026 with Rolldown replacing Rollup, yielding 38-87% faster builds). Not urgent but worth upgrading.
- **Vuetify ^3.4.0** is a few minor versions behind. The caret range will auto-resolve to the latest 3.x on install, so this is only an issue if `node_modules` hasn't been refreshed recently.

---

## 2. Dependency Red Flags

### 2a. Three charting libraries for two charts

This is the most obvious problem in the dependency tree. The codebase ships:

- **Chart.js** (used by `PriceHistory.vue` for a line chart)
- **Highcharts** (used by `BidAskDistribution.vue` for a column chart)
- **ApexCharts** (registered globally in `main.js` but **not visibly used in any component**)

This means:
- ~300-400 KB of unnecessary JavaScript is being bundled (ApexCharts alone is ~180 KB minified).
- Highcharts has a **commercial license requirement** for non-personal use. If this is deployed publicly for a university experiment, the Highcharts license terms should be reviewed.
- Chart.js is the lightest of the three (~65 KB gzipped) and could handle both chart types.

**Recommendation**: Pick one. Chart.js can handle both the line chart and the bar/column chart. Remove Highcharts and ApexCharts entirely. If Highcharts features are genuinely needed (they aren't for a simple bid/ask bar chart), at least remove ApexCharts which appears to be dead code.

### 2b. `webfontloader` (^1.6.28)

This package hasn't been updated since 2017. It works, but it's a zombie dependency. Modern CSS `@font-face` with `font-display: swap` achieves the same result with zero JS. Low priority but worth noting.

### 2c. `lodash` (^4.17.21)

The full lodash bundle is listed as a dependency, but searching the codebase shows it's imported in `TradingDashboard.vue` only via a comment saying "lodash debounce removed." This may be entirely unused. If it is still used elsewhere, switch to individual imports (`lodash-es/debounce`) or native JS equivalents.

### 2d. `haikunator` (^2.1.2)

A random name generator. Niche. Fine if it's used for session/trader name generation; just flagging it as an unusual dependency.

### 2e. No TypeScript

Zero `.ts` files. Zero `lang="ts"` script blocks. Every store, composable, and component is plain JavaScript. For a codebase with 8 stores, cross-store delegation (the `app.js` facade pattern), and real-time WebSocket events, this is a meaningful gap. Type errors in store getters/actions or socket event payloads will only surface at runtime.

---

## 3. Is Vue 3 + Vuetify 3 the Right Choice?

### Vue 3: Yes, defensible

Vue 3 is a solid choice for a trading dashboard in 2026. Key points:

- **Reactivity system** is genuinely well-suited for real-time data. The `reactive()` / `ref()` model with `watchEffect()` maps cleanly to streaming market data, as demonstrated in the socket module and chart watchers.
- **Composition API** is used throughout (all components use `<script setup>`), which is the modern best practice.
- **Performance** is adequate. Vue 3.5's reactivity optimizations are in play. Vue 3.6's Vapor Mode (bypasses Virtual DOM, 2-4x rendering improvement) is in beta and could be an opt-in upgrade path for the highest-frequency components.
- **Ecosystem stability** is strong. Pinia is mature. Vue Router is mature. The community is active.

The main counter-argument would be React, which has a larger ecosystem of pre-built trading components (order books, candlestick charts, etc.). But for a custom-built experiment platform rather than a production brokerage, this ecosystem advantage doesn't matter much.

Svelte would offer better raw rendering performance for high-frequency DOM updates, but the ecosystem is thinner and the team would need to rewrite everything. Not justified.

**Verdict on Vue 3**: Correct choice. No action needed.

### Vuetify 3: Acceptable, but with caveats

Vuetify 3 provides a comprehensive Material Design component set. The codebase uses it for:
- Layout scaffolding (`v-app`, `v-main`, `v-container`, `v-row`, `v-col`)
- App bar, cards, buttons, chips, alerts, snackbars
- Form inputs (text fields, selects) in the admin panel
- Progress indicators

**What Vuetify does well here**: It provides a consistent, responsive grid system and pre-styled components that saved significant development time. The theme configuration in `vuetify.js` is clean and well-structured.

**The concern**: Vuetify is heavy. The full framework adds 200-300 KB to the bundle even with tree-shaking. For a dashboard that's 90% custom-styled (the `TradingDashboard.vue` has 280 lines of custom CSS overriding Vuetify defaults), you're paying the bundle cost for a component library you're mostly fighting against.

**Alternatives worth knowing about** (but not necessarily worth switching to):
- **PrimeVue**: Now the most versatile Vue component library (~480K weekly downloads). Better data tables. Unstyled mode available.
- **Reka UI (formerly Radix Vue)**: Headless components — you get accessibility and behavior without imposed styling. Better fit for heavily custom-designed UIs.
- **Naive UI**: Lighter, TypeScript-first, good theming system.

**Verdict on Vuetify 3**: Adequate. The layout primitives (`v-row`, `v-col`, `v-card`) earn their keep. The heavier components (data tables, form inputs) are only used in the admin panel. Switching would be a multi-week effort for marginal benefit.

---

## 4. Is Vite the Right Build Tool?

**Yes, unambiguously.**

Vite is the standard build tool for Vue projects and has been since ~2022. The current configuration is sensible:
- `vite-plugin-vuetify` for Vuetify auto-imports and tree-shaking
- Path aliases (`@`, `@charts`, `@trading`, etc.) for clean imports
- Manual chunk splitting for vendor code
- HMR configured for localhost development

The one actionable item: **upgrade to Vite 8** when convenient. Vite 8 (March 2026) replaces Rollup with Rolldown (Rust-based bundler), delivering 38-87% faster production builds. The migration guide exists at `main.vite.dev/guide/migration`. This is a low-risk upgrade that would improve CI/CD times.

**Verdict**: Vite is correct. Upgrade to v8 at your convenience.

---

## 5. What Would I Change Starting from Scratch Today?

In priority order:

### 5a. Add TypeScript (High impact)

This is the single highest-value improvement. The store layer has complex cross-store delegation (`app.js` facades to `trader.js` and `orders.js`), and the WebSocket event bus (`mitt`) passes untyped payloads through 15+ event types. A typed event map and typed store interfaces would catch an entire class of bugs at compile time.

Starting from scratch, every `.js` file would be `.ts`, and every `<script setup>` would be `<script setup lang="ts">`.

### 5b. One charting library, not three (High impact)

I'd pick **Lightweight Charts** (by TradingView, MIT licensed, ~40 KB) for the price history and **Chart.js** for the bid/ask distribution. Or just Chart.js for both. Two charts do not need three charting frameworks.

### 5c. Replace Vuetify with a lighter approach (Medium impact)

For a dashboard that's this custom-styled, I'd use:
- **Tailwind CSS** for utility-first styling (eliminates most of the custom CSS)
- **Reka UI** for accessible headless components (modals, dropdowns, tooltips)
- A simple CSS grid for layout (no need for `v-row`/`v-col`)

This would cut 200+ KB from the bundle and eliminate the "fighting against the framework" problem visible in TradingDashboard.vue's extensive CSS overrides.

### 5d. Use `socket.io-client` with typed events (Medium impact)

The current socket module is well-structured (standalone module, mitt bus, not stored in Pinia). But the 15-event `ROUTED_EVENTS` array and the untyped `wsBus.emit/on` calls are fragile. With TypeScript, you'd define a typed event map:

```typescript
type ServerEvents = {
  book_updated: BookUpdatePayload
  transaction_update: TransactionPayload
  time_update: TimePayload
  // ...
}
```

### 5e. Drop the facade store pattern (Low-medium impact)

The `app.js` store is a facade that delegates every getter and action to `trader.js` and `orders.js`. This exists for backward compatibility, but it means every property access goes through an extra indirection layer. Starting fresh, components would import from the specific stores directly.

---

## 6. What's NOT Worth Changing

### 6a. DO NOT switch from Vue to React or Svelte

The codebase has ~20 Vue SFCs, 8 Pinia stores, a router with guards, and a custom design system. Rewriting this in React would take 2-4 weeks and gain nothing measurable. Vue 3's reactivity model is actually a better fit for real-time streaming data than React's re-render model (no `useMemo`/`useCallback` dance needed).

**Cost**: 2-4 weeks. **Benefit**: Zero.

### 6b. DO NOT switch from Pinia to another state manager

Pinia is the official Vue state management library. It's well-integrated, the stores are cleanly structured (the split into trader/orders/market/session/auth/ui is good domain modeling), and the persistence plugin works. There is no better alternative in the Vue ecosystem.

### 6c. DO NOT switch from Socket.IO to raw WebSockets

Socket.IO provides automatic reconnection, room management, and fallback to polling. The current `socket.js` module is well-architected — it keeps the socket instance outside Pinia (avoiding Vue proxy issues), uses mitt for decoupled event routing, and handles reconnection with market re-join. Replacing this with raw WebSockets would mean reimplementing all of this manually.

### 6d. DO NOT migrate to Nuxt/SSR

This is a single-page trading dashboard, not a content site. SSR adds complexity with zero benefit. The SPA model is correct.

### 6e. DO NOT add Tailwind CSS to the existing codebase

Mixing Vuetify's styling system with Tailwind would create a maintenance nightmare. The custom CSS design token system (`design-tokens.css`, `components.css`) is already a reasonable approach. Tailwind would only make sense in a from-scratch rewrite without Vuetify.

### 6f. DO NOT obsess over Vite 7 -> 8 urgency

The upgrade is beneficial but not blocking. Vite 7 builds work fine. Do it when there's a natural pause in feature work, not as a fire drill.

---

## 7. Prioritized Action Items

| Priority | Action | Effort | Impact |
|----------|--------|--------|--------|
| 1 | Remove ApexCharts (unused dead code) | 30 min | Bundle size -180 KB |
| 2 | Consolidate Highcharts -> Chart.js for BidAskDistribution | 2-3 hours | Bundle size -300 KB, eliminate license risk |
| 3 | Audit lodash usage; remove if unused | 30 min | Bundle size -70 KB |
| 4 | Upgrade Vite 7 -> 8 | 1-2 hours | Faster builds (38-87%) |
| 5 | Add TypeScript incrementally (stores first) | 1-2 days | Type safety for the most fragile layer |
| 6 | Remove `webfontloader`, use CSS `@font-face` | 1 hour | Remove zombie dependency |
| 7 | Consider Vuetify -> lighter alternative | 1-2 weeks | Only if doing a major redesign anyway |

---

## Sources

- [React vs Vue vs Svelte: Choosing the Right Frontend Framework in 2026](https://dev.to/_d7eb1c1703182e3ce1782/react-vs-vue-vs-svelte-choosing-the-right-frontend-framework-in-2026-24fk)
- [React vs Vue vs Svelte 2026: Which Frontend Framework Should You Choose?](https://toolboxhubs.com/en/blog/react-vs-vue-vs-svelte-2026)
- [Trading App Tech Stack: Architecture for Low-Latency in 2026](https://www.mobileappdevelopmentcompany.us/trading-app-tech-stack/)
- [Top Vue Component Libraries in 2026](https://uibakery.io/blog/top-vue-component-libraries)
- [Best Vue UI Libraries for 2026](https://www.c-sharpcorner.com/article/best-vue-ui-libraries-for-2026-which-one-should-you-choose/)
- [Vite 8.0 Announcement](https://vite.dev/blog/announcing-vite8)
- [Vue.js Roadmap 2026: Vapor Mode](https://medium.com/@revanthkumarpatha/vue-js-in-2025-vue-js-roadmap-2026-a-clear-performance-first-future-0b3ddabd7b00)
- [Vue 3.6 Vapor Mode Preview](https://vueschool.io/articles/news/vn-talk-evan-you-preview-of-vue-3-6-vapor-mode/)
- [Frontend Technologies for Interactive Trading Dashboards](https://openwebsolutions.in/blog/frontend-technologies-for-trading-dashboards/)
- [Bun vs Vite in 2026](https://www.pkgpulse.com/blog/bun-vs-vite-2026)
