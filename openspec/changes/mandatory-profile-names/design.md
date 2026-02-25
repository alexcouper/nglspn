## Context

Users register with email, password, and kennitala only. The frontend hardcodes `first_name: ""` and `last_name: ""` during registration. Names are optional everywhere — the profile edit form, the API schemas, and the database model all allow blank values. As a result, users appear as "Anonymous" in discussions, project ownership, and public profiles.

The auth routing logic (`getPostAuthDestination`) currently handles one gate: email verification. After that, users go straight to their destination (or `/my-projects`). There is no mechanism to require profile completion before proceeding.

## Goals / Non-Goals

**Goals:**
- Force all users (existing and newly registered) with missing names to provide them before using the platform
- Make the enforcement mechanism generic (`profile_action_required`) so it can be reused for future mandatory profile fields
- Provide a focused `/complete-profile` page for this purpose

**Non-Goals:**
- Changing the registration form or multi-step onboarding flow (separate change)
- Making email verification mandatory (separate change)
- Validating name content beyond non-empty (no real-name verification)
- Removing the "Anonymous" fallback display logic — it stays as a safety net

## Decisions

### 1. Generic `profile_action_required` flag on User model

**Decision**: Add a `BooleanField` `profile_action_required` (default `True`) to the User model rather than checking for empty names at every login.

**Why**: A flag is explicit and extensible. Future requirements (e.g., mandatory bio, accept new ToS) can set this flag without changing the redirect logic. The profile save endpoint re-evaluates whether the flag should remain set based on current validation rules.

**Default `True`**: New users are created needing to complete their profile. The flag is cleared on first successful profile save with valid names. This means enforcement works for new registrations without any changes to the registration flow itself.

**Alternative considered**: Check `not user.first_name or not user.last_name` directly in the frontend routing. Rejected because it couples the redirect logic to specific fields, and doesn't generalize.

### 2. Frontend-driven redirect chain in `getPostAuthDestination`

**Decision**: Extend `getPostAuthDestination` with a second gate: after the `is_verified` check, check `profile_action_required`. If true, redirect to `/complete-profile` (preserving the `next` param).

**Why**: This mirrors the existing `is_verified` pattern exactly. The frontend already calls this function after login and after email verification. Adding one more condition is minimal and consistent.

The login API response (`Token` schema) needs to include `profile_action_required` alongside `is_verified` so the frontend can route correctly without an extra `/me` call.

### 3. `/complete-profile` page

**Decision**: A dedicated page with just first name and last name fields plus a submit button. Submits to the existing `PUT /api/auth/me`. On success, redirects to the original `next` destination or `/my-projects`.

**Why**: Keeps the experience focused — two fields, clear messaging. Reuses the existing profile update API, no new endpoints needed. This page is also used by existing users who are flagged via the data migration.

### 4. Profile save endpoint clears the flag automatically

**Decision**: In the `PUT /api/auth/me` handler, after saving, evaluate whether `profile_action_required` should remain set. Currently this means: if `first_name` and `last_name` are both non-empty (stripped), set `profile_action_required = False`. This evaluation logic lives in one place and can be extended.

**Why**: One endpoint for profile updates keeps things simple. The flag clearing is a side effect of a valid profile update — no separate "complete profile" endpoint needed.

### 5. Data migration for existing users

**Decision**: A Django data migration sets `profile_action_required = True` for all users where `first_name = ''` OR `last_name = ''`. Users who already have both names set get `profile_action_required = False`.

**Why**: This ensures existing users with missing names are caught on their next login. The migration is idempotent and safe to re-run.

### 6. Mandatory name validation on profile save

**Decision**: The `PUT /api/auth/me` endpoint validates that if `first_name` or `last_name` is provided, it must be non-empty (not blank/whitespace). When `profile_action_required` is true, both fields become required in the request.

**Why**: We need server-side enforcement, not just frontend validation. However, we should not break existing profile update calls that only change email preferences — so we only enforce both-required when the flag is set.

## Risks / Trade-offs

- **Existing users forced through profile page**: Users who log in and just want to use the platform will be redirected. This is intentional friction but could cause support tickets. → Mitigation: The `/complete-profile` page is minimal (two fields + submit), with clear messaging.

- **API consumers**: Any non-web client using the login API will now receive `profile_action_required` in the token response. → Mitigation: Currently there is only the web UI.

## Migration Plan

1. Deploy backend changes first (model migration + API changes). New users get `profile_action_required = True` by default.
2. Run data migration to set the flag appropriately for existing users.
3. Deploy frontend changes (routing logic + `/complete-profile` page + mandatory fields on profile edit).
4. Rollback: Remove the frontend routing check. Set `profile_action_required = False` for all users via management command. Backend changes can stay without effect.
