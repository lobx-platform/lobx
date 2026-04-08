# Auth Flow Audit

**Date:** 2026-04-08
**Branch:** `refactor/core-rewrite`
**Scope:** Full authentication flow — frontend stores, HTTP interceptor, Socket.IO, backend endpoints

---

## 1. Current Auth Flow Analysis

The platform supports three distinct login methods, all handled by `Auth.vue` on mount or form submit:

### 1a. Lab Token (`LAB_TOKEN` URL param)

```
URL ?LAB_TOKEN=lab_xxx
  → Auth.vue onMounted detects param (or localStorage fallback)
  → sessionStore.setLabToken(token)  // saves to localStorage separately
  → authStore.labLogin(token)
    → POST /user/login?LAB_TOKEN=lab_xxx
    → backend validates via lab_auth.validate_lab_token()
    → returns trader_id, treatment_group
  → authStore sets user, traderId, labToken in Pinia state
  → authStore.syncToSessionStore() copies traderId to sessionStore
  → NavigationService.afterLogin() routes to onboarding/trading
```

Token lifecycle: generated server-side via `generate_lab_tokens()`, stored in `LAB_TOKENS` dict + persisted to `logs/lab_tokens.json`. Tokens are UUIDs prefixed `lab_`, never expire, and are marked `used: true` on first validation but remain valid forever after.

### 1b. Prolific (`PROLIFIC_PID` URL param)

```
URL ?PROLIFIC_PID=xxx&STUDY_ID=yyy&SESSION_ID=zzz
  → Auth.vue onMounted detects PROLIFIC_PID
  → authStore.prolificLogin(pid, studyId, sessionId)
    → POST /user/login?PROLIFIC_PID=xxx&STUDY_ID=yyy&SESSION_ID=zzz
    → backend creates trader_id = HUMAN_PROLIFIC_{pid}
    → stores user in authenticated_users dict (in-memory only)
  → authStore sets user with isProlific flag
```

No token is issued. The Prolific PID itself becomes the identity. Subsequent HTTP requests rely on the `Bearer` header carrying... nothing useful for Prolific users — there is no token returned that gets stored in `authStore.adminToken` or `authStore.labToken`. **This means Prolific users have no valid Authorization header for subsequent API calls** unless they hit endpoints that resolve identity from the URL path (the `trader_id in lab_trader_map` fallback in `get_current_user`).

### 1c. Admin Password

```
Admin types password → handleAdminLogin()
  → authStore.adminPasswordLogin(password)
    → stores raw password as authStore.adminToken (!)
    → POST /admin/login { password }
    → backend compares to ADMIN_PASSWORD env var
    → returns { is_admin: true, token: ADMIN_PASSWORD }
  → subsequent requests: Authorization: Bearer {raw_password}
```

The raw admin password is persisted to localStorage via Pinia persist config and sent as a Bearer token on every request.

---

## 2. Problems Identified

### P1: Auth state split across three locations

| Data | authStore | sessionStore | localStorage (manual) |
|---|---|---|---|
| `traderId` | yes | yes (synced) | yes (both stores persist) |
| `marketId` | yes | yes | yes (both stores persist) |
| `labToken` | yes | yes | yes (`lab_token` key + both store persists) |
| `onboardingStep` | no | yes | yes (per-user key + store persist) |
| `status` | no | yes | yes |
| `adminToken` | yes | no | yes (auth persist) |
| `user` | yes (not persisted) | no | no |

The `labToken` is stored in **three** separate places: `authStore.labToken`, `sessionStore.labToken`, and `localStorage.lab_token`. On page refresh, `Auth.vue` checks all three (`route.query.LAB_TOKEN || sessionStore.labToken || sessionStore.loadLabToken()`). The `syncToSessionStore()` method in authStore uses a dynamic `import()` to push `traderId` to sessionStore, introducing a race condition.

### P2: Admin password stored as plaintext in localStorage

`authStore.adminToken` is the raw password, persisted via Pinia's `persist` config to localStorage. Any XSS vulnerability exposes the admin password directly. The password is also sent on every HTTP request as `Authorization: Bearer {password}`.

### P3: No token refresh / expiry mechanism

- Lab tokens never expire (no TTL check in `validate_lab_token`)
- Admin "token" is a static password — no session expiry
- Prolific users have no token at all
- No refresh token flow exists
- The 401 interceptor just redirects to `/` without attempting renewal

### P4: Prolific users have broken auth for subsequent requests

After Prolific login, neither `authStore.labToken` nor `authStore.adminToken` is set. The axios interceptor therefore sends **no Authorization header** for Prolific users. Subsequent authenticated API calls only work if:
- The endpoint extracts `trader_id` from the URL path AND
- That `trader_id` exists in `lab_trader_map` (it doesn't — Prolific users are in `authenticated_users`)
- OR the endpoint uses `HUMAN_` prefix path matching (fragile)

### P5: Firebase token verification is dead code

Both `back/api/auth.py` and `back/api/routes/auth.py` contain Firebase `verify_id_token` calls behind try/except blocks. If `firebase_admin` isn't initialized, these silently fail. This is labeled "transitional" but creates confusion about which auth methods are actually supported.

### P6: Socket.IO auth doesn't cover Prolific users

The `_authenticate()` function in `socketio_server.py` checks for `lab_token`, `admin_token`, or `id_token` (Firebase). Prolific users have none of these, so **Socket.IO connections from Prolific users are refused**.

### P7: CORS wildcard on Socket.IO

`cors_allowed_origins="*"` on the Socket.IO server allows any origin to connect. Combined with the password-as-bearer-token pattern, this is a significant risk in production.

### P8: No CSRF protection

The admin login sends the password in a POST body with no CSRF token. Since cookies aren't used for auth, this is less critical, but the lack of any rate limiting on `/admin/login` allows brute-force attacks.

---

## 3. Modern SPA Auth Patterns

### Token Storage Hierarchy (most to least secure)

1. **httpOnly + Secure + SameSite cookies** — invisible to JavaScript, immune to XSS token theft. The gold standard for web apps. Requires backend to set cookies and handle CSRF.
2. **In-memory only (JS variable / Pinia state, no persist)** — lost on page refresh but immune to XSS extraction from storage. Pair with a refresh token in an httpOnly cookie to restore sessions.
3. **sessionStorage** — cleared on tab close. Still vulnerable to XSS.
4. **localStorage** — persists indefinitely, fully accessible to any JS on the page. **Worst option for sensitive tokens.**

### Recommended Pattern for SPAs (2025/2026 consensus)

```
Login:
  POST /auth/login { credentials }
  → Server returns:
    - Short-lived access token (15min) in response body
    - Long-lived refresh token in httpOnly cookie
  → Client stores access token in memory (Pinia state, not persisted)

API calls:
  Authorization: Bearer {access_token}

Token refresh:
  POST /auth/refresh (cookie sent automatically)
  → Server validates refresh cookie, returns new access token
  → If refresh token expired → redirect to login

Page refresh:
  → Access token lost (in-memory only)
  → Silent POST /auth/refresh via httpOnly cookie
  → If valid, restore session without user interaction
```

### For this platform specifically

This is a research experiment platform, not a banking app. The threat model is simpler:
- Lab participants use single-use URLs in a controlled lab environment
- Prolific participants use URLs with embedded IDs from a trusted referrer
- Admin is a single researcher

A pragmatic approach: **issue short-lived JWTs on login, store in memory, use httpOnly refresh cookies for session persistence.**

---

## 4. Recommended Simplified Flow

### Unified login endpoint

Replace three auth paths with one that returns the same shape:

```python
# back/api/routes/auth.py

@router.post("/auth/login")
async def login(request: Request, response: Response):
    body = await request.json()
    method = body.get("method")  # "lab" | "prolific" | "admin"

    if method == "lab":
        user = authenticate_lab(body["token"])
    elif method == "prolific":
        user = authenticate_prolific(body["prolific_pid"], body.get("study_id"), body.get("session_id"))
    elif method == "admin":
        user = authenticate_admin(body["password"])
    else:
        raise HTTPException(401, "Unknown auth method")

    # Issue JWT access token (15 min)
    access_token = create_jwt(user, expires_minutes=15)

    # Issue refresh token as httpOnly cookie (7 days)
    refresh_token = create_refresh_token(user)
    response.set_cookie(
        "refresh_token", refresh_token,
        httponly=True, secure=True, samesite="strict",
        max_age=7 * 86400, path="/auth"
    )

    return {"access_token": access_token, "user": sanitize_user(user)}


@router.post("/auth/refresh")
async def refresh(request: Request, response: Response):
    cookie = request.cookies.get("refresh_token")
    if not cookie:
        raise HTTPException(401, "No refresh token")

    user = verify_refresh_token(cookie)
    new_access = create_jwt(user, expires_minutes=15)

    # Rotate refresh token
    new_refresh = create_refresh_token(user)
    response.set_cookie(
        "refresh_token", new_refresh,
        httponly=True, secure=True, samesite="strict",
        max_age=7 * 86400, path="/auth"
    )

    return {"access_token": new_access}
```

### Unified frontend auth composable

Replace the split between authStore and sessionStore with a single composable:

```javascript
// front/src/composables/useAuth.js
import { ref, computed, readonly } from 'vue'
import axios from '@/api/axios'

// Module-level state (singleton, in-memory only — never persisted to localStorage)
const accessToken = ref(null)
const user = ref(null)
const isRefreshing = ref(false)

export function useAuth() {
  const isAuthenticated = computed(() => !!user.value)
  const isAdmin = computed(() => !!user.value?.is_admin)

  async function login(method, credentials) {
    const { data } = await axios.post('/auth/login', { method, ...credentials })
    accessToken.value = data.access_token
    user.value = data.user
    return data.user
  }

  async function refresh() {
    if (isRefreshing.value) return
    isRefreshing.value = true
    try {
      const { data } = await axios.post('/auth/refresh', {}, { withCredentials: true })
      accessToken.value = data.access_token
      return true
    } catch {
      accessToken.value = null
      user.value = null
      return false
    } finally {
      isRefreshing.value = false
    }
  }

  function logout() {
    accessToken.value = null
    user.value = null
    // Server should clear refresh cookie
    axios.post('/auth/logout', {}, { withCredentials: true }).catch(() => {})
  }

  function getAccessToken() {
    return accessToken.value
  }

  return {
    user: readonly(user),
    isAuthenticated,
    isAdmin,
    login,
    refresh,
    logout,
    getAccessToken,
  }
}
```

### Axios interceptor with silent refresh

```javascript
// front/src/api/axios.js
import axios from 'axios'
import { useAuth } from '@/composables/useAuth'

const instance = axios.create({
  baseURL: import.meta.env.VITE_HTTP_URL,
  withCredentials: true,  // send httpOnly cookies
})

// Attach access token
instance.interceptors.request.use((config) => {
  const { getAccessToken } = useAuth()
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Auto-refresh on 401
let refreshPromise = null

instance.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true

      if (!refreshPromise) {
        const { refresh } = useAuth()
        refreshPromise = refresh().finally(() => { refreshPromise = null })
      }

      const ok = await refreshPromise
      if (ok) {
        // Retry original request with new token
        const { getAccessToken } = useAuth()
        original.headers.Authorization = `Bearer ${getAccessToken()}`
        return instance(original)
      }

      // Refresh failed — redirect to login
      window.location.href = '/'
    }
    return Promise.reject(error)
  }
)

export default instance
```

---

## 5. Socket.IO Authentication

### Current approach (correct pattern, incomplete implementation)

The current code authenticates on connect via the `auth` dict — this is the Socket.IO-recommended approach. The problem is that Prolific users aren't covered, and the admin "token" is a raw password.

### Recommended approach

```javascript
// front/src/store/websocket.js — connect with JWT
import { useAuth } from '@/composables/useAuth'

async initializeWebSocket() {
  const { getAccessToken, refresh } = useAuth()

  let token = getAccessToken()
  if (!token) {
    const ok = await refresh()
    if (!ok) return  // not authenticated
    token = getAccessToken()
  }

  this.socket = io(url.origin, {
    auth: { token },          // JWT, not raw password
    path: sioPath,
    transports: ['websocket', 'polling'],
  })

  // Handle token expiry during long sessions
  this.socket.on('connect_error', async (err) => {
    if (err.message === 'token_expired') {
      const ok = await refresh()
      if (ok) {
        this.socket.auth.token = getAccessToken()
        this.socket.connect()  // retry with new token
      }
    }
  })
}
```

```python
# back/api/socketio_server.py — verify JWT on connect

import jwt

def _authenticate(auth: dict) -> dict | None:
    if not auth:
        return None

    token = auth.get("token")
    if not token:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return {
            "gmail_username": payload["sub"],
            "trader_id": payload["trader_id"],
            "is_admin": payload.get("is_admin", False),
        }
    except jwt.ExpiredSignatureError:
        # Tell client to refresh and reconnect
        raise socketio.exceptions.ConnectionRefusedError("token_expired")
    except jwt.InvalidTokenError:
        return None
```

### Auth on connect vs per-message

| Approach | Pros | Cons |
|---|---|---|
| **Auth on connect** (current) | Simple, one-time check, clean event handlers | Long sessions may outlive token validity |
| **Auth per-message** | Every action is verified | Huge overhead, clutters every handler |
| **Auth on connect + periodic re-auth** (recommended) | Best of both — lightweight handlers, handles expiry | Slightly more complex client logic |

**Recommendation:** Keep auth-on-connect. Add a server-side middleware that checks token expiry periodically (e.g., on each `place_order`) and emits a `token_expired` event if the JWT has lapsed. The client refreshes and reconnects.

---

## 6. Migration Checklist

1. **Add `PyJWT` dependency** to backend, implement `create_jwt()` / `verify_jwt()` helpers
2. **Create `/auth/login` and `/auth/refresh` endpoints** that return JWT + set httpOnly refresh cookie
3. **Replace authStore + sessionStore auth fields** with `useAuth()` composable (in-memory tokens)
4. **Keep sessionStore** for non-auth session state (onboarding step, market progress) — it's fine for that purpose
5. **Update axios interceptor** to use JWT from composable + silent refresh on 401
6. **Update Socket.IO client** to pass JWT in `auth.token`
7. **Update Socket.IO server** `_authenticate()` to verify JWT
8. **Remove Firebase dead code** from `auth.py`, `routes/auth.py`, `socketio_server.py`
9. **Remove `ADMIN_PASSWORD` from localStorage** — stop persisting `adminToken`
10. **Add rate limiting** on `/auth/login` (e.g., 5 attempts per minute per IP)
11. **Set `cors_allowed_origins`** to the actual frontend URL instead of `"*"`

---

## Sources

- [Authentication in SPA the right way (jcbaey)](https://jcbaey.com/authentication-in-spa-reactjs-and-vuejs-the-right-way/)
- [Authentication Patterns and Best Practices for SPAs](https://dev.indooroutdoor.io/authentication-patterns-and-best-practices-for-spas)
- [Please Don't Use JSON Web Tokens for Browser Sessions](https://ianlondon.github.io/posts/dont-use-jwts-for-sessions/)
- [Socket.IO — How to use with JWT](https://socket.io/how-to/use-with-jwt)
- [Socket.IO — Middlewares (auth on connect)](https://socket.io/docs/v4/middlewares/)
- [Securing Socket.IO with Authentication (Medium)](https://medium.com/@mcmohangowda/securing-socket-io-with-authentication-in-node-js-33a6ae8bb534)
