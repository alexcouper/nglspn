## Why

There's no structured onboarding beyond email verification. When we need to collect new information from users (e.g. mandatory names, consent forms, profile photos), there's no mechanism to gate access until they comply — and no way to retroactively require it from existing users who've already logged in. We need a generic onboarding framework that new requirements can plug into, including requirements added after a user has already completed onboarding.

## What Changes

- **New `registration` service (backend)**: A new backend service that owns all onboarding logic. It maintains a registry of onboarding steps, each with a check function that determines whether a user has completed it. The API layer calls into this service to get pending steps for a user — keeping onboarding logic out of the API routers and auth code. Initially ships with just the existing email verification step migrated into this framework.
- **`GET /api/auth/me` includes onboarding state**: The me endpoint calls the registration service to get the user's pending onboarding steps (if any), so the frontend can gate access on login/refresh without extra API calls.
- **Onboarding gate (frontend)**: `getPostAuthDestination` is replaced by a generic onboarding gate. After authentication, the frontend checks for pending steps and routes the user through them in order. Once all steps are complete, the user proceeds to their destination.
- **`/onboarding` page**: A step-based page that renders the appropriate component for each pending step. Steps are rendered one at a time in priority order. The page handles progression and redirects to the final destination when complete.
- **Extensibility contract**: Adding a new onboarding step means: (1) register the step in the registration service with a check function, (2) add a frontend component for that step. No changes to routing, auth, or the onboarding page itself.
- **Retroactive enforcement**: Steps are evaluated dynamically against the current user state, not recorded as "completed at registration time". When a new step is added to the registry, any existing user who doesn't satisfy its check function will be routed through that step on their next login — they only see the steps they haven't completed, not the entire flow again.

## Capabilities

### New Capabilities

- `onboarding-framework`: The backend step registry, the onboarding state on the me endpoint, the frontend onboarding gate, and the `/onboarding` page that renders steps. Covers the extensibility contract for adding new steps.

### Modified Capabilities

_(none)_

## Impact

- **Django backend**: New `registration` service (`services/registration/`) owning the step registry and completion checks, changes to `GET /api/auth/me` response shape to include pending steps
- **Web UI**: New `/onboarding` page, refactor of `getPostAuthDestination` into an onboarding-aware gate, removal of the standalone `/verify-email` redirect (verification becomes an onboarding step)
- **Auth flow**: Post-login routing changes — all onboarding enforcement goes through one path instead of ad-hoc checks
