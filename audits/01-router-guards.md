# Audit 01: Router Guards & Navigation System

**Date**: 2026-04-08
**Scope**: `front/src/router/`, `front/src/services/navigation.js`, `front/src/store/session.js`, `front/src/store/auth.js`
**Branch**: `refactor/core-rewrite`

---

## 1. What's Wrong with the Current Approach

### 1.1 Dual Authority Problem: guards.js vs NavigationService

The system has **two independent decision-makers** for navigation, with overlapping but inconsistent logic:

| Concern | `guards.js` | `NavigationService` |
|---|---|---|
| "Where should authenticated user go?" | L24-27: `getRedirectForStatus(status)` | L27-46: `getRedirectForStatus(status)` (same method) |
| "Can user access trading?" | L43-56: checks `status !== 'trading'`, syncs, redirects | L142-158: `startTrading()` sets status and pushes |
| "What onboarding step?" | L59-73: validates `meta.step` vs `sessionStore.onboardingStep` | L112-123: `nextOnboardingStep()` increments and pushes |
| "Set status on arrival" | L85-97: `afterEach` hook writes status | Components also call `setStatus()` directly |

**The problem**: Guards validate *reactively* (blocking bad navigations), while NavigationService drives *imperatively* (pushing routes). When both fire on the same navigation, they can conflict. For example:

- `NavigationService.afterLogin()` pushes to `consent` (L103-106 of navigation.js)
- The guard's `afterEach` (L94 of guards.js) then sets status to `'onboarding'`
- But `getRedirectForStatus('onboarding')` returns `{ name: 'consent' }` (L34 of navigation.js) regardless of actual progress

This means **a user at step 5 who refreshes gets bounced back to consent** because `getRedirectForStatus('onboarding')` always returns consent, ignoring `onboardingStep`.

### 1.2 Duplicated Constants

`ONBOARDING_ROUTES` is defined in three places:
- `guards.js` L7
- `navigation.js` L9-17
- `session.js` L40 (as `stepRoutes` inside a getter)

Any addition/removal of an onboarding step must be updated in all three. This is a maintenance trap.

### 1.3 The `next()` Anti-Pattern

`guards.js` uses the **deprecated `next()` callback pattern** (L13). Vue Router 4 officially recommends returning a route location object instead. From the [Vue Router docs](https://router.vuejs.org/guide/advanced/navigation-guards.html):

> In previous versions of Vue Router, it was also possible to use a third argument `next`, this was a common source of mistakes and went through an RFC to remove it.

The `next()` pattern is error-prone because:
- Missing a `next()` call silently hangs navigation
- Multiple `next()` calls in branching logic cause unpredictable behavior
- The return-based API is type-safe and composable

### 1.4 Non-Blocking Sync Creates Race Conditions

`guards.js` L77-79:
```js
if (to.meta.requiresSession && !sessionStore.isSyncing) {
  sessionStore.syncFromBackend().catch(() => {})
}
```

This fire-and-forget sync means the guard completes with **stale local state**, then the async sync finishes and updates the store *after* the component has already mounted. If the synced status differs from local state, the user sees a flash of wrong content or gets redirected mid-render.

### 1.5 `afterEach` Overwrites Backend-Synced Status

`guards.js` L85-97 sets `sessionStore.status` based on route name. This is backwards -- **status should drive routing, not the other way around**. When `syncFromBackend()` returns `status: 'trading'` but the user is on the `ready` page (perhaps waiting), the `afterEach` hook overwrites it to `'waiting'`, losing the backend truth.

### 1.6 `loadFromLocalStorage()` Is Never Called

`session.js` defines `loadFromLocalStorage()` at L189-199 but it is **never invoked** anywhere in the codebase. The `persist` config at L204-219 relies on `pinia-plugin-persistedstate`, which is **not installed** (the comment at L173 even acknowledges this). This means:

- On page refresh, Pinia stores start empty
- `sessionStore.onboardingStep` resets to `0`
- The guard at L59-73 sees step 0 and blocks forward navigation
- User gets bounced to consent

**This is the root cause of the consent bounce-back bug.**

### 1.7 Per-User Onboarding Step Is Write-Only

`session.js` L103-115 saves `onboarding_step_{uid}` to localStorage, but **nothing ever reads it back**. There is no `loadPerUserOnboardingStep()` method. The data is written and abandoned.

### 1.8 Plugin Registration Order

`plugins/index.js` L17:
```js
app.use(vuetify).use(router).use(createPinia()).use(MotionPlugin)
```

Router is installed **before** Pinia. The `setupGuards()` function is called during router creation (router/index.js L163), which means the `beforeEach` guard closure captures store references. While Pinia stores are lazily initialized on first `useXxxStore()` call (so this works at runtime), it makes the dependency invisible and fragile. If any guard logic runs during initial route resolution before Pinia is ready, it will throw.

---

## 2. Modern Best Practices (2025-2026)

### 2.1 Return-Based Guards (Vue Router 4 Standard)

The modern pattern replaces `next()` with return values:

```js
router.beforeEach(async (to, from) => {
  if (!isAuthenticated && to.meta.requiresAuth) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  // returning undefined/true = allow navigation
})
```

Sources:
- [Vue Router Navigation Guards](https://router.vuejs.org/guide/advanced/navigation-guards.html)
- [Vue Router 4 Tutorial - Vue School](https://vueschool.io/articles/vuejs-tutorials/how-to-use-vue-router-a-complete-tutorial/)

### 2.2 Route Meta as Single Source of Guard Requirements

Define what each route *needs* in `meta`, and let a single global guard enforce all of them:

```js
{ path: '/trading', meta: { requiresAuth: true, requiredStatus: 'trading' } }
{ path: '/onboarding/consent', meta: { requiresAuth: true, step: 0, flow: 'onboarding' } }
```

### 2.3 Middleware Pipeline Pattern

For complex apps, chain small middleware functions via route meta:

```js
// Route definition
{ path: '/trading', meta: { middleware: [auth, requireStatus('trading')] } }

// Guard
router.beforeEach((to, from) => {
  const middlewares = to.meta.middleware || []
  for (const mw of middlewares) {
    const result = mw(to, from, context)
    if (result) return result  // redirect or false
  }
})
```

This is the pattern recommended by [John Kavanagh's guide](https://johnkavanagh.co.uk/articles/best-practices-for-vue-router-in-large-applications/) and [OneUptime's Vue Router guide](https://oneuptime.com/blog/post/2026-01-24-vue-router-navigation-guards/view).

### 2.4 Composable for Navigation Logic (Vue 3 Idiom)

Replace the `NavigationService` singleton object with a composable:

```js
export function useNavigation() {
  const router = useRouter()
  const session = useSessionStore()
  // ...
}
```

Composables integrate with Vue's reactivity system, are tree-shakeable, and follow Vue 3 conventions.

### 2.5 Single Source of Truth for Flow State

Use the backend-synced status as the authority. Persist to localStorage only as a cache for offline/refresh scenarios, and always prefer backend state when available.

---

## 3. Recommended Architecture

### 3.1 Overview

```
Route Meta (declarative)
    |
    v
Global beforeEach guard (single, return-based)
    |
    +--> auth middleware
    +--> session middleware (await sync)
    +--> flow middleware (onboarding step validation)
    |
    v
Component mounts (no navigation logic in components)
```

### 3.2 Consolidated Route Config

```js
// router/routes.js
export const ONBOARDING_STEPS = [
  { path: 'consent',      name: 'consent',      step: 0, component: () => import('@/pages/onboarding/Consent.vue') },
  { path: 'welcome',      name: 'welcome',      step: 1, component: () => import('@/pages/onboarding/Welcome.vue') },
  // ...
  { path: 'ready',        name: 'ready',         step: 7, component: () => import('@/pages/onboarding/Ready.vue') },
]

// Generate routes from config -- single source of truth
const onboardingChildren = ONBOARDING_STEPS.map(({ path, name, step, component }) => ({
  path,
  name,
  component,
  meta: { requiresAuth: true, flow: 'onboarding', step },
}))
```

### 3.3 Guard as Middleware Pipeline

```js
// router/guard.js
import { useAuthStore } from '@/store/auth'
import { useSessionStore } from '@/store/session'

export function setupGuard(router) {
  router.beforeEach(async (to, from) => {
    const auth = useAuthStore()
    const session = useSessionStore()

    // 1. Restore state on first navigation (cold start)
    if (!session.initialized) {
      await session.initialize()  // load localStorage + sync backend
    }

    // 2. Auth gate
    if (to.meta.requiresAuth && !auth.isAuthenticated) {
      return { name: 'auth', query: to.fullPath !== '/' ? { redirect: to.fullPath } : undefined }
    }

    // 3. Guest-only gate
    if (to.meta.requiresGuest && auth.isAuthenticated) {
      return resolveDestination(session)
    }

    // 4. Admin gate
    if (to.meta.requiresAdmin && !auth.isAdmin) {
      return { name: 'auth' }
    }

    // 5. Flow enforcement
    if (to.meta.flow === 'onboarding') {
      const redirect = enforceOnboardingStep(to.meta.step, session)
      if (redirect) return redirect
    }

    // 6. Status enforcement (trading page needs active market)
    if (to.meta.requiredStatus) {
      if (session.status !== to.meta.requiredStatus) {
        return resolveDestination(session)
      }
    }

    // Allow navigation
  })
}

function resolveDestination(session) {
  // This replaces NavigationService.getRedirectForStatus
  // but also considers onboardingStep for onboarding status
  switch (session.status) {
    case 'onboarding':
    case 'authenticated':
      return { name: ONBOARDING_STEPS[session.onboardingStep]?.name || 'consent' }
    case 'waiting':
      return { name: 'ready' }
    case 'trading':
      return { name: 'trading' }
    case 'summary':
    case 'complete':
      return { name: 'summary' }
    default:
      return { name: 'auth' }
  }
}

function enforceOnboardingStep(targetStep, session) {
  const current = session.onboardingStep

  // Completed users can't go back
  if (current >= 7 && targetStep < 7) {
    return { name: 'ready' }
  }

  // Can't skip ahead
  if (targetStep > current + 1) {
    return { name: ONBOARDING_STEPS[current]?.name || 'consent' }
  }

  return null  // allow
}
```

### 3.4 Session Store with Proper Initialization

```js
// store/session.js (key changes)
export const useSessionStore = defineStore('session', {
  state: () => ({
    // ... existing state ...
    initialized: false,  // NEW: tracks whether state has been restored
  }),

  actions: {
    /**
     * Called once on app cold start (first navigation).
     * Restores localStorage cache, then syncs from backend.
     */
    async initialize() {
      if (this.initialized) return

      // 1. Restore cached state (instant, synchronous)
      this.restoreFromCache()

      // 2. Sync from backend (async, authoritative)
      try {
        await this.syncFromBackend()
      } catch (e) {
        console.warn('Backend sync failed, using cached state')
      }

      // 3. Restore per-user onboarding step
      this.restorePerUserOnboardingStep()

      this.initialized = true
    },

    restoreFromCache() {
      try {
        const stored = localStorage.getItem('session_store')
        if (stored) this.$patch(JSON.parse(stored))
      } catch (e) {
        console.warn('Cache restore failed:', e)
      }
    },

    restorePerUserOnboardingStep() {
      // Actually READ the per-user step that savePerUserOnboardingStep writes
      try {
        const authStore = useAuthStore()
        if (authStore.user?.uid) {
          const saved = localStorage.getItem(`onboarding_step_${authStore.user.uid}`)
          if (saved !== null) {
            const step = parseInt(saved, 10)
            if (!isNaN(step) && step >= 0 && step <= 7) {
              this.onboardingStep = step
              this.hasCompletedOnboarding = step >= 7
            }
          }
        }
      } catch (e) {
        // Ignore
      }
    },
  },
})
```

### 3.5 useNavigation Composable (Replaces NavigationService)

```js
// composables/useNavigation.js
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/store/session'
import { useAuthStore } from '@/store/auth'
import { ONBOARDING_STEPS } from '@/router/routes'

export function useNavigation() {
  const router = useRouter()
  const session = useSessionStore()
  const auth = useAuthStore()

  async function afterLogin() {
    await session.initialize()

    if (auth.isAdmin) {
      session.setOnboardingStep(7)
      session.setStatus('waiting')
      return router.push({ name: 'ready' })
    }

    const step = session.onboardingStep || 0
    if (step >= 7) {
      session.setStatus('waiting')
      return router.push({ name: 'ready' })
    }

    session.setStatus('onboarding')
    return router.push({ name: ONBOARDING_STEPS[step].name })
  }

  function nextStep() {
    const current = session.onboardingStep
    if (current >= 7) return
    session.setOnboardingStep(current + 1)
    return router.push({ name: ONBOARDING_STEPS[current + 1].name })
  }

  function prevStep() {
    const current = session.onboardingStep
    if (current <= 0) return
    session.setOnboardingStep(current - 1)
    return router.push({ name: ONBOARDING_STEPS[current - 1].name })
  }

  async function logout() {
    const { useWebSocketStore } = await import('@/store/websocket')
    const { useTraderStore } = await import('@/store/app')
    useWebSocketStore().disconnect()
    useTraderStore().clearStore()
    session.reset()
    auth.logout()
    return router.push({ name: 'auth' })
  }

  return { afterLogin, nextStep, prevStep, logout }
}
```

### 3.6 Remove afterEach Status Sync

Delete the `afterEach` hook entirely. Status should be set explicitly by actions (login, startTrading, onTradingEnded), not inferred from the current route name.

---

## 4. The Consent Bounce-Back Bug: Root Cause & Fix

### 4.1 Root Cause Chain

1. User completes onboarding to step 5 (or any step > 0)
2. `session.savePerUserOnboardingStep()` writes `onboarding_step_{uid} = 5` to localStorage
3. `session.saveToLocalStorage()` writes full state including `onboardingStep: 5`
4. User refreshes the page (or closes and reopens)
5. **Neither `loadFromLocalStorage()` nor `restorePerUserOnboardingStep()` is ever called on startup**
6. Pinia initializes `onboardingStep` to `0` (the default from `state()`)
7. `pinia-plugin-persistedstate` is not installed, so the `persist` config is dead code
8. Guard at `guards.js` L59-73 sees `currentProgress = 0`, user is trying to go to step 5
9. `targetStep (5) > currentProgress (0) + 1` evaluates to `true`
10. Guard redirects to `ONBOARDING_ROUTES[0]` = `'consent'`

Additionally, `NavigationService.getRedirectForStatus('onboarding')` (L34) always returns `{ name: 'consent' }` regardless of the user's actual step. So even the "authenticated user redirect" path bounces to consent.

### 4.2 Immediate Fix (Minimal Change)

Apply these three changes without restructuring:

**Fix A: Call `loadFromLocalStorage` on store creation**

In `front/src/store/session.js`, add an `$onAction` or use a Pinia plugin. Simplest approach -- call it in the guard before any logic:

```js
// guards.js, inside beforeEach, before any checks:
if (!sessionStore._restored) {
  sessionStore.loadFromLocalStorage()
  // Also restore per-user step
  const uid = authStore.user?.uid
  if (uid) {
    const saved = localStorage.getItem(`onboarding_step_${uid}`)
    if (saved !== null) {
      const step = parseInt(saved, 10)
      if (!isNaN(step)) sessionStore.onboardingStep = step
    }
  }
  sessionStore._restored = true
}
```

**Fix B: Fix `getRedirectForStatus` to respect onboarding progress**

In `front/src/services/navigation.js` L33-34, change:

```js
// Before:
case 'onboarding':
  return { name: 'consent' }

// After:
case 'onboarding': {
  const step = useSessionStore().onboardingStep || 0
  return { name: ONBOARDING_ROUTES[Math.min(step, ONBOARDING_ROUTES.length - 1)] }
}
```

**Fix C: Install `pinia-plugin-persistedstate` or remove the dead `persist` config**

Either:
```bash
bun add pinia-plugin-persistedstate
```
And register it:
```js
// plugins/index.js
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)
app.use(pinia)
```

Or remove the `persist` config from both stores to avoid confusion.

### 4.3 Proper Fix (Recommended Refactor)

Implement section 3 above. The key principle: **the guard must `await` session initialization before making any routing decision**. The `session.initialize()` pattern (section 3.4) ensures state is always restored before the first guard check runs.

---

## 5. Migration Plan

### Phase 1: Fix the Bug (30 min)
- Apply Fix A, B, C from section 4.2
- Verify: login as Prolific user, complete 3 onboarding steps, refresh, confirm resumption at step 3

### Phase 2: Modernize Guards (1-2 hours)
- Replace `next()` with return-based guards
- Move `ONBOARDING_STEPS` to a single shared constant
- Add `session.initialize()` and call it in the guard
- Remove `afterEach` status-setting hook
- Delete `NavigationService.getRedirectForStatus` (inline into guard's `resolveDestination`)

### Phase 3: Replace NavigationService with Composable (1 hour)
- Create `composables/useNavigation.js`
- Update `Auth.vue`, `UserLanding.vue`, `0.vue`, `8.vue`, `MarketSummary.vue`, `TradingDashboard.vue` to use composable
- Delete `services/navigation.js`

### Phase 4: Fix Plugin Order (5 min)
- In `plugins/index.js`, register Pinia before Router:
  ```js
  app.use(pinia).use(router).use(vuetify).use(MotionPlugin)
  ```

---

## 6. Files Referenced

| File | Key Issues |
|---|---|
| `front/src/router/index.js` | Route definitions (OK), legacy redirects (OK) |
| `front/src/router/guards.js` | Deprecated `next()`, non-blocking sync (L77), afterEach status overwrite (L85-97) |
| `front/src/services/navigation.js` | Overlaps with guards, `getRedirectForStatus` ignores step (L34), singleton anti-pattern |
| `front/src/store/session.js` | `loadFromLocalStorage` never called (L189), per-user step write-only (L103), persist config is dead (L204) |
| `front/src/store/auth.js` | `persist` config also dead (L128), duplicates `traderId`/`marketId` with session store |
| `front/src/plugins/index.js` | Router registered before Pinia (L17) |
| `front/src/components/Auth.vue` | Calls `NavigationService.afterLogin()` imperatively (L86, L102) |
| `front/src/components/UserLanding.vue` | Calls `NavigationService` for prev/next (L146-150), duplicates step logic |
| `front/src/components/pages/0.vue` | Calls `NavigationService.nextOnboardingStep()` directly (L325) |
| `front/src/components/pages/8.vue` | Multiple watchers for trading start, fallback setTimeout (L215-228) |

---

## Sources

- [Vue Router Navigation Guards (official docs)](https://router.vuejs.org/guide/advanced/navigation-guards.html)
- [Best Practices for Vue Router in Large Applications](https://johnkavanagh.co.uk/articles/best-practices-for-vue-router-in-large-applications/)
- [How to Configure Vue Router Navigation Guards (2026)](https://oneuptime.com/blog/post/2026-01-24-vue-router-navigation-guards/view)
- [Vue Router 4 Complete Tutorial - Vue School](https://vueschool.io/articles/vuejs-tutorials/how-to-use-vue-router-a-complete-tutorial/)
