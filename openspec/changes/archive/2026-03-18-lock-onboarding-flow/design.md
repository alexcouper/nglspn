## Context

The onboarding framework redirects users to `/onboarding` after login when they have pending steps. However, once on that page, nothing prevents navigation to authenticated routes via the nav bar or direct URL entry. The `useRequireAuth` hook only checks authentication status, not onboarding completion. The `Navigation` component shows all authenticated links regardless of onboarding state.

User state (including `pending_onboarding_steps`) is already loaded once into React context on app mount — no additional API calls are needed.

## Goals / Non-Goals

**Goals:**
- Prevent users with pending onboarding steps from accessing authenticated routes
- Remove navigation affordances that would lead users away from onboarding
- Keep logout accessible so users aren't trapped

**Non-Goals:**
- Blocking access to public pages (about, projects, competitions) — these are harmless
- Backend enforcement — the backend already returns pending steps; the frontend is responsible for routing
- Next.js middleware — the existing hook-based approach is sufficient

## Decisions

### Enforce onboarding in `useRequireAuth` hook
Add a check for `user.pending_onboarding_steps.length > 0` to the existing `useRequireAuth` hook. If the user has pending steps and is not already on `/onboarding`, redirect to `/onboarding`.

**Why this over middleware:** There's no Next.js middleware in the app today. The hook already runs on every authenticated page. Adding a condition to it is minimal and consistent with the existing pattern. Middleware would require extracting user state from the JWT or making an API call — unnecessary complexity.

**Why this over a wrapper component:** A hook is already the established pattern. Adding a component would be a different paradigm for the same concern.

### Hide authenticated nav links during onboarding
The `Navigation` component already conditionally renders "My Projects" and "My Reviews" based on `isAuthenticated`. Add an additional condition: user must also have no pending onboarding steps. The UserMenu (which contains logout) remains visible.

**Why hide rather than disable:** Disabled links suggest "you'll get access later" which is correct, but hidden links are cleaner — fewer things to look at, less confusion. The onboarding page itself communicates what needs to happen.

### Skip redirect when already on `/onboarding`
The onboarding page uses `useRequireAuth`. Without an exclusion, users with pending steps would get an infinite redirect loop. Check `pathname` before redirecting.

## Risks / Trade-offs

- **Client-side only enforcement** → Users could theoretically bypass via browser devtools or direct API calls. Acceptable because the backend already returns the correct data; this is a UX gate, not a security boundary.
- **Brief flash on direct URL navigation** → If a user types `/my-projects` directly, they'll see the page start to load before being redirected. This is inherent to client-side routing and acceptable for this use case.
