## Why

Discussion textareas are fixed-size (2-3 rows) with resizing disabled, making it awkward to write longer messages. There's also no way to edit a discussion or reply after posting — the only option is to delete and re-post, which loses the thread context and timestamp.

## What Changes

- Add auto-expanding textarea behavior to discussion and reply forms — the textarea grows as the user types, up to a sensible maximum height, then scrolls
- Add edit functionality for discussions and replies — authors can edit their own posts
- Add a backend API endpoint for updating discussion body
- Show an "edited" indicator on posts that have been modified

## Capabilities

### New Capabilities

- `discussion-editing`: Covers the ability for authors to edit their own discussions and replies, including the API endpoint, UI controls, and edited indicator display

### Modified Capabilities

- `discussions`: The existing discussions spec gains a new PATCH endpoint for editing, and the response shape gains an `is_edited` field. The textarea UI behavior changes from fixed-size to auto-expanding.

## Impact

- **Backend**: New PATCH endpoint on discussions router, service layer update method, possible model field or logic for tracking edits
- **Frontend**: Changes to `NewDiscussionForm.tsx`, `ReplyForm.tsx`, `DiscussionList.tsx` for auto-expanding textareas and edit UI
- **API types**: OpenAPI spec regeneration needed after backend changes
