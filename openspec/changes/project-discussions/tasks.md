## 1. Discussions Django App & Model

- [x] 1.1 Create `apps/discussions/` Django app with `models.py`, `apps.py`, `admin.py`, `__init__.py`
- [x] 1.2 Implement `Discussion` model with UUID pk, project FK, author FK (SET_NULL on delete), parent FK (nullable self-ref), body, created_at, updated_at
- [x] 1.3 Register the app in Django settings
- [x] 1.4 Create and run migrations
- [x] 1.5 Register `Discussion` in Django admin

## 2. Discussions Service Layer

- [x] 2.1 Create `services/discussions/handler_interface.py` with `create_discussion` and `delete_discussion` methods
- [x] 2.2 Create `services/discussions/query_interface.py` with `list_for_project` and `get_by_id` methods
- [x] 2.3 Create `services/discussions/django_impl/` with handler and query implementations
- [x] 2.4 Ensure `create_discussion` sets project from parent when creating a reply
- [x] 2.5 Ensure `delete_discussion` checks requesting user is the author
- [x] 2.6 Register discussions service on `HANDLERS` and `REPO` in `services/__init__.py`

## 3. Discussions API

- [x] 3.1 Create `api/schemas/discussion.py` with request/response schemas (include author id, first_name, last_name, replies list)
- [x] 3.2 Create `api/routers/discussions.py` with JWT-authenticated endpoints: GET list, POST create, POST reply, DELETE
- [x] 3.3 Register the discussions router in `api/main.py`
- [x] 3.4 Write tests for discussions API endpoints (auth required, CRUD, author-only delete, 403 on others' delete)

## 4. Notifications Django App & Model

- [x] 4.1 Create `apps/notifications/` Django app with `models.py`, `apps.py`, `admin.py`, `__init__.py`
- [x] 4.2 Implement `Notification` model with UUID pk, recipient FK, discussion FK, cadence (IMMEDIATE/HOURLY/DAILY/NEVER choices), sent (bool), created_at, sent_at (nullable)
- [x] 4.3 Register the app in Django settings
- [x] 4.4 Create and run migrations
- [x] 4.5 Register `Notification` in Django admin

## 5. User Notification Frequency Setting

- [x] 5.1 Add `notification_frequency` CharField to User model with choices IMMEDIATE/HOURLY/DAILY/NEVER, default IMMEDIATE
- [x] 5.2 Create and run migration
- [x] 5.3 Add `notification_frequency` to `UserResponse` and `UserUpdate` API schemas
- [x] 5.4 Write test for updating notification frequency via user API

## 6. Notifications Service Layer

- [x] 6.1 Create `services/notifications/handler_interface.py` with `create_notifications_for_discussion`, `send_immediate_notifications`, `send_batch_notifications` methods
- [x] 6.2 Create `services/notifications/django_impl/` with handler implementation
- [x] 6.3 Implement recipient determination: project owner + root discussion author + previous participants, deduplicated, excluding comment author
- [x] 6.4 Skip notification creation for users with NEVER cadence
- [x] 6.5 Snapshot user's `notification_frequency` as the notification's cadence at creation time
- [x] 6.6 Send email immediately for IMMEDIATE cadence notifications on creation
- [x] 6.7 Register notifications service on `HANDLERS` in `services/__init__.py`
- [x] 6.8 Write tests for recipient determination (all deduplication and exclusion scenarios from spec)

## 7. Notification Async Tasks

- [x] 7.1 Create `api/tasks/notifications.py` with `create_discussion_notifications` task that calls the notifications service
- [x] 7.2 Wire discussion service `create_discussion` to enqueue `create_discussion_notifications` task after creating a discussion/reply
- [x] 7.3 Create `send_hourly_notifications` task that calls `send_batch_notifications(HOURLY)`
- [x] 7.4 Create `send_daily_notifications` task that calls `send_batch_notifications(DAILY)`
- [x] 7.5 Write tests for async notification creation flow

## 8. Notification Email Templates

- [x] 8.1 Create immediate notification email template (project name, discussion link, comment author, comment body)
- [x] 8.2 Create digest notification email template (grouped by project and discussion)
- [x] 8.3 Add `send_discussion_notification_email` and `send_discussion_digest_email` methods to email handler interface and implementation

## 9. OpenAPI & TypeScript Types

- [x] 9.1 Run `make extract-openapi` to regenerate OpenAPI spec
- [x] 9.2 Run `npm run generate-types` in web-ui to generate TypeScript types

## 10. Project Page Layout Rework

- [x] 10.1 Create shared `ProjectTitleBanner` component with project name, author name (linked), author email, and starred image with CSS rotation
- [x] 10.2 Handle no-image case in the banner (render without image, no broken layout)
- [x] 10.3 Create `ProjectNav` component with Info/Discussions navigation links, highlighting the active view
- [x] 10.4 Refactor `/projects/[id]/page.tsx` to use the new title banner and nav, with Info content (description, additional images, tags) below

## 11. Discussions Frontend

- [x] 11.1 Create `/projects/[id]/discussions/page.tsx` as a dynamic (non-SSG) route sharing the title banner layout
- [x] 11.2 Build discussion list component showing root discussions with flat replies, author attribution, and timestamps
- [x] 11.3 Build new discussion form (textarea + submit)
- [x] 11.4 Build reply form (inline reply textarea under a discussion)
- [x] 11.5 Build delete button for own discussions
- [x] 11.6 Implement unauthenticated view: sign-up/login prompt with no discussion content shown
- [x] 11.7 Wire frontend to discussions API endpoints (list, create, reply, delete)

## 12. Notification Frequency Settings UI

- [x] 12.1 Add sticky sliding scale component for notification frequency (Every Time / At most every hour / At most every day / Never)
- [x] 12.2 Integrate the slider into the user settings page, wired to the user update API

## 13. Linting & Tests

- [x] 13.1 Run `make lint` in django-backend and fix any issues
- [x] 13.2 Run `npm run lint` in web-ui and fix any issues
- [x] 13.3 Run `make test` in django-backend and ensure all tests pass
