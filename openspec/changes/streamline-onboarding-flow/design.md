## Context

Post-authentication routing currently has a single hard-coded gate: email verification. The `getPostAuthDestination` function checks `user.is_verified` and redirects to `/verify-email` if false, otherwise sends the user to their destination. There is no backend concept of onboarding — the User model has `is_verified` but nothing generic for tracking what a user still needs to do.

The existing service layer uses an interface/implementation pattern: abstract interfaces in `handler_interface.py`, Django implementations in `django_impl/`, and services wired via `HANDLERS`/`REPO` singletons in `services/__init__.py`.

## Goals / Non-Goals

**Goals:**
- A `registration` service that owns the concept of onboarding steps and can evaluate which steps a user still needs to complete
- `GET /api/auth/me` returns pending steps so the frontend can gate access in one check
- A single `/onboarding` page that renders steps sequentially without needing modification when steps are added
- Email verification migrated to be the first onboarding step
- Existing users who don't satisfy a newly added step are caught on next login

**Non-Goals:**
- Persisting step completion records — steps are evaluated dynamically via check functions against current user state
- Adding any new onboarding steps beyond email verification (that comes in `mandatory-profile-names`)
- Multi-page onboarding with separate URLs per step — it's one page that swaps content
- Progress bar or step indicators — can be added later but not in scope

## Decisions

### 1. New `registration` service with in-code step registry

The step registry is a Python list of step definitions in the service, not a database table. Each step is a dataclass with `id` (string), `priority` (int), and `check` (callable that takes a User and returns bool — `True` means complete).

**Why not a database table?** Steps are defined by code (each needs a check function and a frontend component). A DB table would add migration overhead for what's essentially a code-level concern. The registry is the source of truth; adding a step is adding code, not data.

**Why not decorators or auto-discovery?** Explicit registration in one place makes the step order obvious and reviewable. A list in the service module is simple and sufficient.

**Structure:**

```
services/registration/
├── handler_interface.py      # get_pending_steps(user) -> list[OnboardingStep]
├── steps.py                  # Step dataclass + registry list
└── django_impl/
    ├── __init__.py
    └── handler.py            # DjangoRegistrationHandler
```

The service is query-only (no write operations — steps are evaluated, not mutated), but we'll use the handler pattern since it's called from the API layer and may gain write operations later (e.g. if a step needs to record something).

### 2. `pending_onboarding_steps` on the me endpoint response

Add a `pending_onboarding_steps: list[str]` field to `UserResponse`. The `/me` endpoint calls `HANDLERS.registration.get_pending_steps(user)` and maps the result to step IDs.

**Why on `/me` and not a separate endpoint?** The frontend already calls `/me` on login/refresh to get user state. Adding onboarding state here avoids an extra round trip and keeps all "what does the frontend need to know about this user" in one place.

**Why a list of strings, not objects?** The frontend only needs step IDs to know which components to render and in what order. Step metadata (title, description) lives in the frontend components themselves — the backend shouldn't own UI copy.

### 3. Frontend: replace `getPostAuthDestination` with onboarding-aware gate

The current `getPostAuthDestination` function is replaced. The new logic:

1. After login/register, the frontend fetches `/me` (already happens via `refreshUser`)
2. If `pending_onboarding_steps` is non-empty → redirect to `/onboarding?next=<destination>`
3. If empty → redirect to destination (or `/my-projects`)

This lives in the same `auth-routing.ts` module. The `/verify-email` specific redirect is removed.

### 4. `/onboarding` page with component map

The onboarding page maintains a `Record<string, ComponentType<OnboardingStepProps>>` mapping step IDs to React components. Each component receives:

```typescript
interface OnboardingStepProps {
  onComplete: () => void;  // called when step is done
}
```

The page:
1. Reads `pending_onboarding_steps` from the user context
2. Renders the component for the first step
3. On `onComplete`, calls `refreshUser()` to get updated pending steps
4. If steps remain, renders the next one; if empty, redirects to destination

**Why `refreshUser` after each step?** The backend is the source of truth for step completion. Re-fetching ensures frontend and backend agree. This also handles edge cases where completing one step might affect another.

The existing `/verify-email` page content is extracted into a `VerifyEmailStep` component that implements `OnboardingStepProps`. The page itself (`/verify-email`) can redirect to `/onboarding` for backwards compatibility.

### 5. Email verification: first registered step

The `verify-email` step is registered with priority `100` (leaving room for lower-priority steps to be inserted before it, though email verification should typically be first). Its check function: `lambda user: user.is_verified`.

The existing backend endpoints (`POST /api/auth/verify-email`, `POST /api/auth/resend-verification`) remain unchanged — the step component calls them directly. No backend changes needed for verification itself.

### 6. Login endpoint: drop `is_verified` from token response

Currently the login endpoint returns `is_verified` in the token response so the frontend can decide where to redirect. With the onboarding framework, the frontend gets this from `/me` instead. The `is_verified` field on the token response becomes redundant.

However, to avoid a breaking change during rollout, keep `is_verified` on the token response for now and remove it in a follow-up cleanup.

## Risks / Trade-offs

**[Check functions called on every `/me` request]** → Each step's check function runs when the user hits `/me`. With a small number of steps checking in-memory user fields, this is negligible. If a step ever needs a DB query, it should be optimised (e.g. select_related or caching). For now, all checks are simple attribute lookups.

**[Frontend component map must be kept in sync with backend registry]** → If a backend step is registered but the frontend has no component for it, the onboarding page would break. Mitigated by: (1) adding both in the same PR, (2) the onboarding page falling through gracefully if a step ID is unknown (log a warning, skip it).

**[`/verify-email` URL may be bookmarked or linked]** → Redirect `/verify-email` to `/onboarding` to maintain backwards compatibility. The old page becomes a simple redirect.
