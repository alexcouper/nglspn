## Why

Users appear as "Anonymous" in discussions, project ownership, and public profiles because first/last names are optional and most users never fill them in. This undermines community trust and makes the platform feel impersonal.

## What Changes

- **`complete-profile` onboarding step**: Register a new step in the onboarding framework's step registry. The check function considers the step complete when the user has either a first_name or last_name set. Priority is after email verification.
- **`CompleteProfileStep` component**: A new onboarding step component that renders first name and last name fields. Submits to the existing `PUT /api/auth/me`. Mapped in the frontend step component registry.
- **Profile edit page validation**: Make first_name and last_name required on the profile edit form so users can't remove their names once set.
- **Profile save endpoint validation**: The `PUT /api/auth/me` endpoint enforces that users cannot save an empty first_name AND last_name (at least one must be non-empty).

## Capabilities

### New Capabilities

- `mandatory-profile-names`: Covers the `complete-profile` onboarding step registration, the `CompleteProfileStep` frontend component, and mandatory field enforcement on profile save.

### Modified Capabilities

_(none — the onboarding framework is used as-is, no spec changes needed)_

## Impact

- **Django backend**: New onboarding step in the step registry, profile update endpoint validation
- **Web UI**: New `CompleteProfileStep` onboarding component, profile form validation changes
- **No model migration needed** — the onboarding framework evaluates steps dynamically against current user state
- **No data migration needed** — existing users with missing names will see the step on next login automatically
