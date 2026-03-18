## Context

Users register with email, password, and kennitala only. The frontend hardcodes `first_name: ""` and `last_name: ""` during registration. Names are optional everywhere — the profile edit form, the API schemas, and the database model all allow blank values. As a result, users appear as "Anonymous" in discussions, project ownership, and public profiles.

The onboarding framework is now in place. It provides a step registry in the backend (`ONBOARDING_STEPS` in `services/registration/steps.py`), a `pending_onboarding_steps` field on the `/me` response, frontend routing that redirects to `/onboarding` when steps are pending, and a step component registry (`ONBOARDING_STEP_COMPONENTS`) that maps step IDs to React components. Email verification is already implemented as the first onboarding step.

## Goals / Non-Goals

**Goals:**
- Force all users (existing and newly registered) with missing names to provide at least one name before using the platform
- Build on the onboarding framework — no new model fields, no standalone pages, no data migrations

**Non-Goals:**
- Requiring both first and last name (either one is sufficient)
- Validating name content beyond non-empty (no real-name verification)
- Removing the "Anonymous" fallback display logic — it stays as a safety net
- Changing the registration form itself

## Decisions

### 1. Register a `complete-profile` onboarding step

**Decision**: Add a new `OnboardingStep` to `ONBOARDING_STEPS` with `id="complete-profile"`, `priority=200`, and a check function that returns `True` when the user has either a non-empty `first_name` or `last_name` (after stripping whitespace).

**Why**: The onboarding framework evaluates steps dynamically against user state. No model field or data migration needed — existing users with no names will see the step automatically on next login, and new users (who register with empty names) will see it after email verification.

**Priority 200**: Placed after `verify-email` (priority 100). Users verify their email first, then complete their profile. This ordering makes sense because email verification is a harder gate (code entry) while profile completion is quick.

### 2. `CompleteProfileStep` frontend component

**Decision**: Create a `CompleteProfileStep` component following the same pattern as `VerifyEmailStep`. Renders first name and last name inputs, submits to `PUT /api/auth/me`, and calls `onComplete` on success. Register it in `ONBOARDING_STEP_COMPONENTS` as `"complete-profile"`.

**Why**: The onboarding page already handles step sequencing, auth guards, and destination preservation. The component only needs to handle its own form logic. Reusing `PUT /api/auth/me` means no new API endpoints.

**Form behavior**: Both fields are shown but only one needs to be non-empty. This is a low-friction ask — users can provide whichever name they prefer.

### 3. Server-side validation on profile save

**Decision**: Add validation to `PUT /api/auth/me` that prevents saving when the result would leave both `first_name` and `last_name` empty. This applies to all users, not just those in onboarding. The validation checks the *resulting* state (considering both provided and existing values), not just the request payload.

**Why**: Without server-side enforcement, users could clear their names via the profile edit page after completing onboarding, then appear as "Anonymous" again. The onboarding step would catch them on next login, but preventing it at the API level is cleaner.

**Partial updates**: The `UserUpdate` schema uses `None` for unchanged fields. If a user only updates `notification_frequency`, names aren't in the payload and existing names are preserved — validation passes.

### 4. Profile edit page form validation

**Decision**: Add client-side validation to the profile edit form that prevents submission when both name fields would be empty. Show a validation error message.

**Why**: Matches the server-side validation. Users get immediate feedback rather than a 400 error after submission.

## Risks / Trade-offs

- **Existing users forced through onboarding**: Users with no names who log in will be routed to `/onboarding` to complete their profile. This is intentional friction but minimal — one or two fields, then they proceed. The onboarding page provides a consistent experience for all onboarding steps.

- **Only one name required**: We're not forcing both names. This means some users may only provide a first name or only a last name. This is an acceptable trade-off — any name is better than "Anonymous", and forcing both feels unnecessarily strict for a platform that supports Icelandic naming conventions.

## Migration Plan

1. Deploy backend changes: add step to registry + profile save validation. Zero-downtime, no migrations.
2. Deploy frontend changes: add `CompleteProfileStep` component + profile edit validation.
3. Rollback: Remove the step from `ONBOARDING_STEPS` and remove validation. No data cleanup needed.
