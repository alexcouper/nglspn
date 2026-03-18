## Why

Project approval currently requires access to the Django admin UI, which is IP-restricted. This creates a bottleneck — only people with admin access from allowed IPs can approve projects. Adding a MODERATOR group with a dedicated "Pending Projects" view in the web UI lets trusted users manage project approvals from anywhere without needing Django admin access.

## What Changes

- New Django auth group `MODERATOR` that grants project moderation privileges
- New API endpoint to list pending projects (accessible to moderators)
- New API endpoint to change project status (approve, reject, ice-box) as a moderator
- New "Pending Projects" tab in the user dropdown menu for moderator users
- New frontend page showing pending projects with actions to approve/reject/ice-box
- Current user API response includes group membership so the frontend can show/hide moderator UI

## Capabilities

### New Capabilities

- `moderator-role`: MODERATOR group definition, membership check, and API-level authorization for moderation actions
- `project-moderation-ui`: Frontend page listing pending projects with status transition controls, accessible from user menu

### Modified Capabilities

_(none — existing specs unchanged)_

## Impact

- **Django backend**: New API router for moderation endpoints, group check middleware/dependency, user serializer updated to include groups
- **Web UI**: New page component, new user menu entry, new API client calls
- **Auth context**: Frontend auth context needs to expose user groups
- **OpenAPI**: New endpoints require type regeneration for web-ui
