## 1. MODERATOR Group & Authorization

- [ ] 1.1 Create data migration to add MODERATOR Django auth group
- [ ] 1.2 Add `MODERATOR_GROUP_NAME = "MODERATOR"` constant
- [ ] 1.3 Create `require_moderator` authorization helper that checks group membership or superuser status, returning 403/401 as appropriate
- [ ] 1.4 Write tests for the authorization helper (moderator allowed, superuser allowed, regular user denied, unauthenticated denied)

## 2. Moderation API Endpoints

- [ ] 2.1 Extract approval/rejection side effects (email, revalidation) from admin actions into a shared service function
- [ ] 2.2 Update admin actions to use the shared service function
- [ ] 2.3 Create `api/routers/moderation.py` with `GET /api/moderation/projects` endpoint — list pending projects ordered by `created_at` ascending
- [ ] 2.4 Create `POST /api/moderation/projects/{project_id}/status` endpoint — change status with optional rejection reason, using the shared service function for side effects
- [ ] 2.5 Add moderation router to the API configuration
- [ ] 2.6 Write tests for list pending projects (returns pending only, empty list, auth required, moderator-only)
- [ ] 2.7 Write tests for status change (approve, reject with reason, ice-box, 404 for missing project, auth checks)

## 3. OpenAPI & Type Generation

- [ ] 3.1 Regenerate OpenAPI spec (`make extract-openapi`)
- [ ] 3.2 Regenerate TypeScript types (`npm run generate-types`)

## 4. Frontend — User Menu

- [ ] 4.1 Update `UserMenu` to show "Pending Projects" link when `user.groups` includes `MODERATOR`

## 5. Frontend — Moderation Page

- [ ] 5.1 Create `/moderation` page with authentication and moderator group guard
- [ ] 5.2 Fetch and display pending projects (title, owner, submission date, main image)
- [ ] 5.3 Add approve and ice-box action buttons per project
- [ ] 5.4 Add reject action with required reason input
- [ ] 5.5 Handle empty state when no projects are pending
- [ ] 5.6 Remove project from list on successful status change

## 6. Verification

- [ ] 6.1 Run backend linting (`make lint`)
- [ ] 6.2 Run backend tests (`make test`)
- [ ] 6.3 Run frontend linting (`npm run lint`)
- [ ] 6.4 Manual test: assign MODERATOR group to test user via Django admin, verify menu link appears, approve/reject a project
