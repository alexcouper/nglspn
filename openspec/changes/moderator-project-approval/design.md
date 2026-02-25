## Context

Project approval is currently handled exclusively through the Django admin UI, which is IP-restricted. The `ProjectStatus` model already supports `pending`, `approved`, `rejected`, and `ice_box` states. Admin actions in `ProjectAdmin` handle bulk approve/reject with side effects (email notifications, cache revalidation). The `UserResponse` schema already resolves and returns `groups: list[str]` from Django auth groups — so the frontend already receives group membership data.

## Goals / Non-Goals

**Goals:**
- Allow users in a MODERATOR group to view and moderate pending projects from the web UI
- Reuse existing `ProjectStatus` transitions and side effects (emails, revalidation)
- Keep the admin approval path working as-is

**Non-Goals:**
- Self-service moderator signup or role requests
- Granular permissions (e.g., approve-only vs reject-only)
- Audit log beyond what `approved_by` already provides
- Moderator management UI — admins assign the MODERATOR group via Django admin

## Decisions

### 1. Use Django auth groups, not a custom role model

The `MODERATOR` group is a standard Django auth group. Created via a data migration. Membership is managed through Django admin (add user to group). This avoids a custom role model and leverages the existing `UserResponse.resolve_groups` which already returns group names to the frontend.

**Alternative considered**: Boolean `is_moderator` field on User. Rejected because Django groups are the standard mechanism and the schema already supports them.

### 2. New `moderation` API router under `/api/moderation/`

A new `api/routers/moderation.py` with:
- `GET /api/moderation/projects` — list pending projects (paginated)
- `POST /api/moderation/projects/{project_id}/status` — change project status

Both endpoints require authentication + MODERATOR group membership. The status change endpoint reuses the same side-effect logic as admin actions (approval emails, cache revalidation).

**Alternative considered**: Extending `/api/my/projects` with a query param. Rejected because moderation is a distinct capability — separate router keeps concerns clean and authorization simple.

### 3. Authorization via a reusable `require_moderator` dependency

A helper function that checks `request.auth.groups.filter(name="MODERATOR").exists()` and returns 403 if not a member. Used as a decorator or inline check in the moderation router. Superusers also pass this check.

### 4. Frontend: new `/moderation` page + user menu entry

- `UserMenu` checks if `user.groups` includes `"MODERATOR"` and conditionally renders a "Pending Projects" link
- New `/moderation` page lists pending projects with approve/reject/ice-box action buttons
- Each action calls `POST /api/moderation/projects/{id}/status` with the target status
- Rejection requires a reason (text input) before submitting

### 5. Reuse existing side effects from admin actions

The admin `approve_projects` action enqueues `send_project_approved_email` and `revalidate_project` tasks. Extract this logic into a shared service function so both admin actions and the moderation API call the same code path. This avoids duplicating email/revalidation logic.

## Risks / Trade-offs

- **Risk**: Moderator accidentally ice-boxes an approved project → Mitigation: confirmation dialog on destructive actions in the UI. The status change endpoint allows any valid transition, matching admin behavior.
- **Risk**: Group name mismatch between backend and frontend → Mitigation: use a constant `MODERATOR_GROUP_NAME = "MODERATOR"` in the backend; frontend checks against the same string.
- **Trade-off**: No pagination on pending projects initially — pending projects are typically a small set (<50). Can add pagination later if needed.
