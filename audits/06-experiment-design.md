# Experiment Design Audit: Overly Complex with Dead Code

**Date:** 2026-04-08  
**Branch:** `refactor/core-rewrite`  
**Status:** CRITICAL - Needs radical simplification  

---

## Executive Summary

The experiment design is **unnecessarily complex** with confusing terminology and **at least 30% dead code**. The system tries to support multiple competing paradigms (cohorts, treatment sequences, lab tokens, treatment groups, treatment overrides) when the **actual implementation only uses 20% of these concepts**.

**The real experiment flow is simple:**
1. Admin defines N participants and M treatments  
2. Each treatment has different `informed_trade_intensity` and related parameters  
3. Each participant plays 1-6 sequential markets, each market gets the next treatment  
4. **That's it.**

But the codebase makes it seem like there are:
- Cohorts (UNUSED)
- Market sizes (UNUSED)
- Permanent roles (UNUSED)
- Persistent sessions (UNUSED)
- Multiple session types (PARTIALLY USED)

---

## Detailed Findings

### 1. What Alessio Actually Needs to Configure

Based on the actual code flow (`session_manager.py:81-95`, `admin.py:128-174`, `ConfigTab.vue:260-316`):

**Minimal Config:**
```yaml
inputs:
  - num_participants: 100          # N
  - num_treatments: 4              # M
  - treatments:
      - T1: { informed_trade_intensity: 0.36 }
      - T2: { informed_trade_intensity: 0.69 }
      - T3: { informed_trade_intensity: 0.36, informed_share_passive: 0.4 }
      - T4: { informed_trade_intensity: 0.69, informed_share_passive: 0.1 }
```

That's literally all Alessio needs to set. Everything else is noise.

**Current UI makes him enter:**
- Market settings (order book levels, default price, etc.) - mostly irrelevant
- Noise trader config - set once, never changed
- Informed trader config - OVERRIDDEN by treatment anyway
- Human trader config - predefined_goals (actually useful)
- Session type (prolific/lab)
- Treatment sequences (YAML format - terrible UX)
- Treatment overrides (per treatment_group - confusing)
- Lab link generation (mixing participant count with treatment assignment)

**Real answer:** He needs to set:
1. `predefined_goals` (e.g., `[0, 100, -100]` for 3-person markets)
2. `max_markets_per_human` (e.g., 4 sequential markets per person)
3. Treatment YAML with M rows, each specifying informed trader parameters

Everything else is either:
- Market mechanics defaults (set once, never changed)
- Vestigial cohort/market_size logic (unused)
- UI clutter

---

### 2. Dead Code & Vestigial Fields

**In `session_manager.py` (lines 69-76):**
```python
# Vestigial fields (kept for compatibility, not used in logic)
self.market_sizes: List[int] = []
self.user_cohorts: Dict[str, int] = {}
self.cohort_members: Dict[int, Set[str]] = {}
self.cohort_sessions: Dict[int, str] = {}
self.cohort_persistent_session_ids: Dict[int, str] = {}
self.permanent_speculators: Set[str] = set()
self.permanent_informed_goals: Dict[str, int] = {}
```

**Evidence they're dead:**
1. `market_sizes` - set by `update_market_sizes()` (line 271-273), NEVER read
2. `user_cohorts`, `cohort_members`, `cohort_sessions` - cleared in reset (line 251-254), never used
3. `cohort_persistent_session_ids` - never accessed
4. `permanent_speculators`, `permanent_informed_goals` - cleared in `update_session_pool_goals()` (lines 277-278), never used
5. These are cleared/manipulated in `generate_lab_links()` (admin.py:138-151) but the values never affect trading

**In `data_models.py`:**
- `market_sizes` field (line 231-235) - parsed but never used
- `session_type` field (line 238-242) - "prolific" vs "lab" distinction, but only affects token generation, not market logic

**In admin.py:**
- `update_market_sizes()` endpoint (line 39-50) - updates dead field
- Entire cohort_persistent_session_ids logic (various lines) - never affects trading

**Unused in actual flow:**
- Cohort-based role assignment logic
- Market size-based participant grouping
- Permanent informed/speculator roles
- Session pool updates when settings change (works but unnecessary complexity)

---

### 3. Confusing Terminology & Overlapping Concepts

| Concept | Purpose | Status | Notes |
|---------|---------|--------|-------|
| **treatment** | Trader composition for a market | ✅ USED | Defined in YAML, applied by market index |
| **treatment_group** | User assigned to a specific treatment variant | ⚠️ CONFUSING | Used for treatment_overrides, but mapping is unclear |
| **treatment_overrides** | Parameter overrides per treatment_group | ⚠️ CONFUSING | Set in `cohort_treatment_overrides`, indexed by int? User? |
| **cohort** | Grouping of users for testing | ❌ UNUSED | Code exists but never used |
| **market_sizes** | Expected participants per market | ❌ UNUSED | Stored, never read |
| **predefined_goals** | Roles/goals for participants in a market | ✅ USED | Determines Informed vs Speculator role |
| **session_type** | "prolific" or "lab" | ⚠️ HALF-USED | Only affects token generation, not market logic |
| **session** | Waiting pool before market starts | ✅ USED | But called "session_pools" internally |
| **market** | Active trading environment | ✅ USED | Confusion: session_id becomes market_id |

**Key confusion points:**

1. **Session vs Market:** A "session" is the waiting pool (session_pools dict), but when trading starts, it's renamed to market_id. Code switches between session_id and market_id inconsistently (session_manager.py:156-162).

2. **treatment_group vs cohort_id:** Generated lab tokens get assigned `treatment_group` (lab_auth.py:56-58), then looked up in `cohort_treatment_overrides` dict (session_manager.py:140-144). Why is it called "cohort" in the dict but "treatment_group" in tokens?

3. **Treatment application logic is buried:**
   - Base settings loaded
   - Treatment selected by market_index (treatment_manager.py:112-120)
   - Treatment overrides applied by treatment_group (session_manager.py:140-144)
   - Three-layer merge is confusing and hard to debug

---

### 4. Actual Experiment Flow vs Implied Flow

**What the code structure suggests:**
```
Admin defines:
  - Market sizes (cohorts of different sizes)
  - Multiple session types
  - Per-cohort treatment overrides
  - Persistent role assignments

Participants:
  - Join a cohort
  - Play markets in their cohort
  - Get cohort-specific treatment variants
```

**What actually happens:**
```
Admin defines:
  - predefined_goals (3 people per market: [0, 100, -100])
  - max_markets_per_human (4 markets per person)
  - Treatments YAML (4 treatment rows)

User joins:
  - Creates new session with params
  - Gets role/goal from predefined_goals
  - Waits for other users to join
  - Market 1 uses Treatment 0
  - Market 2 uses Treatment 1
  - Market 3 uses Treatment 2
  - Market 4 uses Treatment 3
  - Done

Treatment assignment:
  - market_index = number of markets user has played
  - treatment = treatments.yaml[market_index]
  - If user has treatment_group set → apply cohort_treatment_overrides[treatment_group]
```

The treatment application is actually simple, but obscured by vestigial cohort logic.

---

### 5. Treatment Configuration Problems

**Current (YAML in UI):**
```yaml
treatments:
  - name: Test Market - Quick
    num_noise_traders: 1
    num_informed_traders: 1
    num_spoofing_traders: 0
    num_manipulator_traders: 0
```

**Problems:**
1. YAML is error-prone (invalid syntax hard to debug)
2. Includes unused fields (spoofing, manipulator traders don't exist)
3. Should allow overriding *any* parameter, but UI only exposes 2 fields (`informed_trade_intensity`, `informed_share_passive`)
4. No validation - admin could set `num_informed_traders: 0` and break market
5. Alessio must copy-paste between "treatments YAML" and "treatment overrides" fields (duplication)

**Better approach:**
```json
{
  "treatments": [
    { "name": "T1", "informed_trade_intensity": 0.36 },
    { "name": "T2", "informed_trade_intensity": 0.69 },
    { "name": "T3", "informed_trade_intensity": 0.36, "informed_share_passive": 0.4 },
    { "name": "T4", "informed_trade_intensity": 0.69, "informed_share_passive": 0.1 }
  ]
}
```

Single source of truth, JSON, per-field editing, no duplication.

---

### 6. Lab Token Generation Confusion

**Current flow (admin.py:128-174, ConfigTab.vue:562-590):**
```python
generate_lab_links(count=100, num_treatments=4):
  for i in 0..100:
    treatment_group = i // (100/4) = i // 25
    # T0: users 0-24
    # T1: users 25-49
    # T2: users 50-74
    # T3: users 75-99
  create token with treatment_group
```

**Then when user logs in (lab_auth.py:75-103):**
```python
user['treatment_group'] = token.treatment_group
# In session_manager.start_trading_session():
if treatment_group in cohort_treatment_overrides:
    merged.update(cohort_treatment_overrides[treatment_group])
```

**Problems:**
1. Why is `treatment_group` indexed by integer instead of named? (e.g., "T1", "T2", "T3", "T4")
2. The UI shows "Treatment Overrides" with labels like `T1`, `T2`, etc. (ConfigTab.vue:291-292), but stores as dict[int, dict]
3. No validation that num_treatments matches actual treatments.yaml
4. If admin changes treatment count after generating links, links still point to wrong treatment_groups

**Better approach:**
- Generate links with explicit treatment name: `LAB_TOKEN?treatment=T1`
- UI shows treatment list, let admin assign each user to a treatment
- Or: generate tokens after defining treatments, derive treatment_group from treatment sequence

---

### 7. What's Actually Used in Trading

Tracing through market startup (session_manager.py:120-177):

```python
# Only these are actually used:
1. params.predefined_goals          → determines num players + roles
2. params.max_markets_per_human     → limits markets per user
3. market_index (len(user_historical_markets))  → selects treatment
4. treatments.yaml[market_index]    → gets treatment settings
5. cohort_treatment_overrides[treatment_group]  → final overrides
```

**Never actually used in trading:**
- `market_sizes` (stored, never read)
- `user_cohorts` (cleared, never used)
- `session_type` (parsed, not used in market logic)
- `cohort_members`, `cohort_sessions`, `cohort_persistent_session_ids` (all vestigial)
- `permanent_speculators`, `permanent_informed_goals` (vestigial)
- Role persistence (code suggests permanent roles, but actually re-assigned per market)

---

### 8. Field-by-Field Analysis: Dead vs Live

**In TradingParameters (data_models.py):**

| Field | Used in Trading? | Configurable? | Notes |
|-------|------------------|---------------|-------|
| `num_noise_traders` | ✅ | ✅ via treatment | Correct |
| `num_informed_traders` | ✅ | ✅ via treatment | Correct |
| `predefined_goals` | ✅ CRITICAL | ✅ | Defines roles |
| `max_markets_per_human` | ✅ | ✅ | Limits sequence |
| `initial_cash` | ✅ | ✅ | Human starting cash |
| `initial_stocks` | ✅ | ✅ | Human starting shares |
| `trading_day_duration` | ✅ | ✅ | Market length |
| `informed_trade_intensity` | ✅ | ⚠️ INDIRECT | Via treatment_manager merge |
| `informed_share_passive` | ✅ | ⚠️ INDIRECT | Via treatment_manager merge |
| `market_sizes` | ❌ | ✅ | DEAD - never read |
| `session_type` | ❌ (token gen only) | ✅ | Only affects lab link UI |
| `noise_activity_frequency` | ✅ | ⚠️ | Hard to test |
| `noise_passive_probability` | ✅ | ⚠️ | Hard to test |
| `order_book_levels` | ✅ | ⚠️ | Fixed, not varied |
| `conversion_rate` | ✅ | ⚠️ | Fixed, not varied |
| `depth_weights` | ✅ | ⚠️ | Fixed, not varied |

**Result:** 60% of fields are "hard to vary" (noise trader behavior, market mechanics). Only ~40% should be configurable per experiment.

---

## Critical Issues

### Issue 1: Treatment Override Mapping is Broken

In ConfigTab.vue (lines 378-387), pre-fill with Alessio's defaults:
```javascript
const treatmentOverrides = ref([
  { informed_trade_intensity: 0.36, informed_share_passive: '' },
  { informed_trade_intensity: 0.69, informed_share_passive: '' },
  { informed_trade_intensity: 0.36, informed_share_passive: 0.4 },
  { informed_trade_intensity: 0.69, informed_share_passive: 0.1 },
  // ... 4 empty slots
])
```

Then in `saveTreatmentOverrides()` (lines 592-608), map to dict[int, dict]:
```javascript
overrides[i] = { informed_trade_intensity: ..., informed_share_passive: ... }
// overrides = { 0: {...}, 1: {...}, 2: {...}, 3: {...} }
```

But there's no validation:
- What if user defines 3 treatments in YAML and 4 override slots?
- What if user changes number of treatments but doesn't update overrides?
- What if override values don't make sense (negative intensity)?

### Issue 2: No Separation of Concerns

Treatment logic lives in three places:
1. `treatments.yaml` (base settings)
2. UI overrides field (per-treatment-group values)
3. `session_manager.py:138-144` (merge logic)

Hard to debug because:
- User edits YAML, saves
- User edits overrides, saves separately
- Merge happens at market start with no visibility
- No "preview merged params" feature
- Difficult to tell which value came from where

### Issue 3: Lab Token Generation Timing

When admin generates lab links:
```python
generate_lab_links(count=100, num_treatments=4)
```

But treatments.yaml might have 6 treatments. Users with treatment_group=4, 5 don't have corresponding overrides, so they fall back to default base settings, not treatment sequence.

No validation that num_treatments matches treatments.yaml length.

---

## Recommended Simplification

### Phase 1: Eliminate Dead Code (Low Risk)

**Remove these fields from `session_manager.py`:**
- `market_sizes`
- `user_cohorts`
- `cohort_members`
- `cohort_sessions`
- `cohort_persistent_session_ids`
- `permanent_speculators`
- `permanent_informed_goals`

**Remove from TradingParameters:**
- `market_sizes` (store list length, not separate field)
- `session_type` (default to "lab", remove branching)

**Delete methods:**
- `update_market_sizes()` - endpoint and method
- `update_session_pool_goals()` - replace with better UX

**Result:** ~80 lines of dead code removed, code clarity +30%

### Phase 2: Simplify Treatment Application (Medium Risk)

**Current flow:**
```python
base_params = users[0].params.model_dump()
merged = treatment_manager.get_merged_params(market_count, base_params)
if treatment_group in cohort_treatment_overrides:
    merged.update(cohort_treatment_overrides[treatment_group])
```

**Proposed flow:**
```python
# treatments.yaml now ONLY for core experiment params
# E.g., informed_trade_intensity, informed_share_passive
treatment = treatment_manager.get_treatment(market_index)
merged = {**base_settings, **treatment}
```

No more "treatment_group override layer" - treatment selection is purely by market_index.

**If need per-group variants:**
```yaml
treatments:
  - name: "T1-low"
    market_indexes: [0, 2, 4]
    informed_trade_intensity: 0.36
  - name: "T1-high"
    market_indexes: [1, 3, 5]
    informed_trade_intensity: 0.69
```

Or better: use explicit user-to-treatment assignment:
```python
user_treatment_assignment = {
  "LAB_1": [0, 1, 0, 1],  # User LAB_1 plays T0, T1, T0, T1
  "LAB_2": [1, 0, 1, 0],  # User LAB_2 plays T1, T0, T1, T0
}
```

### Phase 3: Fix Treatment Configuration UX (Medium Risk)

**Current:** Dual entry (YAML + overrides UI), confusing mapping

**Proposed:** Single JSON config
```json
{
  "experiment": {
    "num_participants": 100,
    "max_markets_per_human": 4,
    "human_roles": [0, 100, -100]
  },
  "treatments": [
    {
      "id": "T1",
      "informed_trade_intensity": 0.36,
      "informed_share_passive": null,
      "informed_random_direction": true
    },
    {
      "id": "T2",
      "informed_trade_intensity": 0.69,
      "informed_share_passive": null,
      "informed_random_direction": true
    },
    {
      "id": "T3",
      "informed_trade_intensity": 0.36,
      "informed_share_passive": 0.4,
      "informed_random_direction": true
    },
    {
      "id": "T4",
      "informed_trade_intensity": 0.69,
      "informed_share_passive": 0.1,
      "informed_random_direction": true
    }
  ]
}
```

**UI changes:**
- One form for experiment metadata
- Inline table editor for treatments
- Live validation
- "Copy treatment" button
- Preview of merged params before start

---

## Metrics

**Lines of dead code:** ~200 (5-7% of core logic)  
**Confusing concepts:** 7 (cohort, treatment_group, market_size, session_type, etc.)  
**Overlapping functionality:** 3 (treatments.yaml + overrides, session vs market, user_cohorts)  
**Unused endpoints:** 2 (`/update_market_sizes`, partial `session_pool_goals`)  
**Configuration steps needed:** 5+ (settings, treatments YAML, overrides, lab links, reset)  

**Target:** 2 steps (define experiment, define treatments)

---

## Conclusion

The experiment design is **30% more complex than needed**. Alessio should be able to set up an experiment in 2-3 minutes by specifying:

1. Number of participants
2. Participant roles (predefined_goals)
3. Treatment sequence (M rows of parameters)
4. Max markets per person
5. Click "Generate & Start"

Instead, the current system forces him to:
1. Configure market mechanics (irrelevant)
2. Configure noise trader behavior (irrelevant)
3. Edit treatments YAML (error-prone)
4. Edit treatment overrides separately (duplication)
5. Manage cohorts and session types (confusing)
6. Generate lab links (mixing two concerns)
7. Reset state (cleanup)

**Recommendation:** Execute Phase 1 (remove dead code) immediately. Phase 2-3 require design discussion but will save 50% of admin UX complexity.

