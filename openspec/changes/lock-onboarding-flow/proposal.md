## Why

Users can bypass the onboarding flow by clicking navigation links (My Projects, My Reviews) or manually navigating to authenticated routes. The onboarding framework gates users at login, but doesn't prevent them from leaving once they're on `/onboarding`. Required steps like email verification can be ignored entirely.

## What Changes

- `useRequireAuth` hook will redirect users with pending onboarding steps back to `/onboarding`, preventing access to authenticated routes
- Navigation component will hide authenticated-only links (My Projects, My Reviews, Profile) when the user has pending onboarding steps, keeping only logout available
- Public pages remain accessible — the lock only applies to authenticated routes that use `useRequireAuth`

## Capabilities

### New Capabilities

_None — this extends the existing onboarding framework._

### Modified Capabilities

- `onboarding-framework`: Adding a requirement that authenticated routes enforce the onboarding gate, and that navigation hides authenticated links during onboarding

## Impact

- `src/web-ui/src/hooks/useRequireAuth.ts` — add onboarding step check and redirect
- `src/web-ui/src/components/Navigation.tsx` — conditionally hide links during onboarding
- `src/web-ui/src/lib/auth-routing.ts` — may need to expose helper or adjust `AUTH_PAGES` list
