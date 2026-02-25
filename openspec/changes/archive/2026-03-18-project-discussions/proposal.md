## Why

Projects currently have no way for users to provide feedback, ask questions, or discuss the work. Adding threaded discussions to project pages creates community engagement and gives project owners valuable feedback. The notification system ensures participants stay informed without being overwhelmed.

## What Changes

- **Project page rework**: Replace the current boxed layout with a title banner (project name, author, email, starred image with CSS rotation) and a tabbed content area (Info / Discussions). Discussions live at a separate route (`/projects/[id]/discussions`) since the content is dynamic and auth-gated
- **Discussions**: New Django app (`apps/discussions/`) with threaded comment model (tree structure), exposed through a new service layer and API. Frontend renders a flat discussion view (no nested replies for now). Only authenticated users can post or read discussions
- **Notifications**: New Django app and service for tracking and delivering notifications when discussions receive activity. Supports immediate, hourly, and daily delivery cadences via django-tasks. A sliding scale control (Every Time / At most every hour / At most every day / Never) in user settings, applying to all projects for that user
- **Notification delivery**: Comment creation triggers async notification creation for project owner, discussion creator, and discussion participants (deduplicated per user per comment). Immediate notifications sent on creation; hourly and daily batches handled by scheduled tasks

## Capabilities

### New Capabilities

- `discussions`: Threaded discussion/comment model, new Django app and service layer, API endpoints, and frontend discussion view on project pages
- `notifications`: Notification persistence, async creation on comment events, email delivery with immediate/hourly/daily cadences, user-level frequency setting
- `project-page-layout`: Reworked project page with title banner, starred image treatment, and Info/Discussions navigation with discussions at a separate route

### Modified Capabilities

_No existing specs to modify._

## Impact

- **Backend**: Two new Django apps (`discussions`, `notifications`), new service layers following the existing handler/query pattern, new API routers via Django Ninja, new django-tasks for hourly/daily notification batches
- **User model**: New `notification_frequency` field added for discussion notification preferences
- **Frontend**: Project detail page restructured with title banner and Info/Discussions navigation. Discussions at a separate dynamic route. New discussion components. User settings UI updated for notification frequency preference
- **API**: New endpoints for discussions CRUD. Modified user settings endpoints (new notification frequency field)
- **Email**: New notification email templates leveraging existing email service infrastructure
