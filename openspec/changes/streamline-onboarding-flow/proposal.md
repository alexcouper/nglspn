## Why

The current registration flow is disjointed: users register, may or may not verify their email (it's currently optional/skippable), and land directly on `/my-projects` with an incomplete profile. With `mandatory-profile-names` enforcing name collection, we have an opportunity to turn registration into a coherent multi-step onboarding experience where each step is required before proceeding.

**Depends on**: `mandatory-profile-names` (provides the `profile_action_required` flag and `/complete-profile` page)

## What Changes

- **Multi-step onboarding**: Registration becomes a guided flow from the user's perspective: credentials (email, password, kennitala) → verify email → enter name → done. Each step is required.
- **Mandatory email verification**: Email verification can no longer be skipped. Users cannot proceed past verification until confirmed. The current flow allows unverified users to reach the platform.
- **Onboarding UX**: Progress indicators, consistent styling, and welcoming copy across the registration steps to make it feel like one cohesive process rather than separate pages.

## Capabilities

### New Capabilities

- `onboarding-flow`: Covers the multi-step registration experience, mandatory email verification enforcement, and the guided UX tying the steps together.

### Modified Capabilities

_(none)_

## Impact

- **Web UI**: Registration page, verify-email page, and complete-profile page need to be connected as a flow with progress indicators
- **Django backend**: May need to enforce email verification server-side (currently only a frontend concern)
- **Auth routing**: `getPostAuthDestination` gates need to be strictly ordered: verify email → complete profile → destination
