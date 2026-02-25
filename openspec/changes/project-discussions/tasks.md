## 1. Discussions Django App & Model

- [ ] 1.1 Create `apps/discussions/` Django app with `models.py`, `apps.py`, `admin.py`, `__init__.py`
- [ ] 1.2 Implement `Discussion` model with UUID pk, project FK, author FK (SET_NULL on delete), parent FK (nullable self-ref), body, created_at, updated_at
- [ ] 1.3 Register the app in Django settings
- [ ] 1.4 Create and run migrations
- [ ] 1.5 Register `Discussion` in Django admin

## 2. Discussions Service Layer

- [ ] 2.1 Create `services/discussions/handler_interface.py` with `create_discussion` and `delete_discussion` methods
- [ ] 2.2 Create `services/discussions/query_interface.py` with `list_for_project` and `get_by_id` methods
- [ ] 2.3 Create `services/discussions/django_impl/` with handler and query implementations
- [ ] 2.4 Ensure `create_discussion` sets project from parent when creating a reply
- [ ] 2.5 Ensure `delete_discussion` checks requesting user is the author
- [ ] 2.6 Register discussions service on `HANDLERS` and `REPO` in `services/__init__.py`

## 3. Discussions API

- [ ] 3.1 Create `api/schemas/discussion.py` with request/response schemas (include author id, first_name, last_name, replies list)
- [ ] 3.2 Create `api/routers/discussions.py` with JWT-authenticated endpoints: GET list, POST create, POST reply, DELETE
- [ ] 3.3 Register the discussions router in `api/main.py`
- [ ] 3.4 Write tests for discussions API endpoints (auth required, CRUD, author-only delete, 403 on others' delete)

## 4. Notifications Django App & Model

- [ ] 4.1 Create `apps/notifications/` Django app with `models.py`, `apps.py`, `admin.py`, `__init__.py`
- [ ] 4.2 Implement `Notification` model with UUID pk, recipient FK, discussion FK, cadence (IMMEDIATE/HOURLY/DAILY/NEVER choices), sent (bool), created_at, sent_at (nullable)
- [ ] 4.3 Register the app in Django settings
- [ ] 4.4 Create and run migrations
- [ ] 4.5 Register `Notification` in Django admin

## 5. User Notification Frequency Setting

- [ ] 5.1 Add `notification_frequency` CharField to User model with choices IMMEDIATE/HOURLY/DAILY/NEVER, default IMMEDIATE
- [ ] 5.2 Create and run migration
- [ ] 5.3 Add `notification_frequency` to `UserResponse` and `UserUpdate` API schemas
- [ ] 5.4 Write test for updating notification frequency via user API

## 6. Notifications Service Layer

- [ ] 6.1 Create `services/notifications/handler_interface.py` with `create_notifications_for_discussion`, `send_immediate_notifications`, `send_batch_notifications` methods
- [ ] 6.2 Create `services/notifications/django_impl/` with handler implementation
- [ ] 6.3 Implement recipient determination: project owner + root discussion author + previous participants, deduplicated, excluding comment author
- [ ] 6.4 Skip notification creation for users with NEVER cadence
- [ ] 6.5 Snapshot user's `notification_frequency` as the notification's cadence at creation time
- [ ] 6.6 Send email immediately for IMMEDIATE cadence notifications on creation
- [ ] 6.7 Register notifications service on `HANDLERS` in `services/__init__.py`
- [ ] 6.8 Write tests for recipient determination (all deduplication and exclusion scenarios from spec)

## 7. Notification Async Tasks

- [ ] 7.1 Create `api/tasks/notifications.py` with `create_discussion_notifications` task that calls the notifications service
- [ ] 7.2 Wire discussion service `create_discussion` to enqueue `create_discussion_notifications` task after creating a discussion/reply
- [ ] 7.3 Create `send_hourly_notifications` task that calls `send_batch_notifications(HOURLY)`
- [ ] 7.4 Create `send_daily_notifications` task that calls `send_batch_notifications(DAILY)`
- [ ] 7.5 Write tests for async notification creation flow

## 8. Notification Email Templates

- [ ] 8.1 Create immediate notification email template (project name, discussion link, comment author, comment body)
- [ ] 8.2 Create digest notification email template (grouped by project and discussion)
- [ ] 8.3 Add `send_discussion_notification_email` and `send_discussion_digest_email` methods to email handler interface and implementation

## 9. OpenAPI & TypeScript Types

- [ ] 9.1 Run `make extract-openapi` to regenerate OpenAPI spec
- [ ] 9.2 Run `npm run generate-types` in web-ui to generate TypeScript types

## 10. Project Page Layout Rework

- [ ] 10.1 Create shared `ProjectTitleBanner` component with project name, author name (linked), author email, and starred image with CSS rotation
- [ ] 10.2 Handle no-image case in the banner (render without image, no broken layout)
- [ ] 10.3 Create `ProjectNav` component with Info/Discussions navigation links, highlighting the active view
- [ ] 10.4 Refactor `/projects/[id]/page.tsx` to use the new title banner and nav, with Info content (description, additional images, tags) below

## 11. Discussions Frontend

- [ ] 11.1 Create `/projects/[id]/discussions/page.tsx` as a dynamic (non-SSG) route sharing the title banner layout
- [ ] 11.2 Build discussion list component showing root discussions with flat replies, author attribution, and timestamps
- [ ] 11.3 Build new discussion form (textarea + submit)
- [ ] 11.4 Build reply form (inline reply textarea under a discussion)
- [ ] 11.5 Build delete button for own discussions
- [ ] 11.6 Implement unauthenticated view: sign-up/login prompt with no discussion content shown
- [ ] 11.7 Wire frontend to discussions API endpoints (list, create, reply, delete)

## 12. Notification Frequency Settings UI

- [ ] 12.1 Add sticky sliding scale component for notification frequency (Every Time / At most every hour / At most every day / Never)
- [ ] 12.2 Integrate the slider into the user settings page, wired to the user update API

## 13. Linting & Tests

- [ ] 13.1 Run `make lint` in django-backend and fix any issues
- [ ] 13.2 Run `npm run lint` in web-ui and fix any issues
- [ ] 13.3 Run `make test` in django-backend and ensure all tests pass
