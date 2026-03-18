## Context

Discussions currently use fixed-size textareas (3 rows for new discussions, 2 rows for replies) with `resize-none`. Authors can delete their own posts but cannot edit them. The model already has `updated_at` (auto_now), so we can detect edits by comparing `updated_at` to `created_at`.

## Goals / Non-Goals

**Goals:**
- Auto-expanding textareas that grow with content up to a max height, then scroll
- Edit functionality for discussion authors (both root discussions and replies)
- Visual indicator for edited posts

**Non-Goals:**
- Edit history / revision tracking
- Markdown or rich text editing
- Admin/moderator editing of other users' posts

## Decisions

### 1. Auto-expanding textarea approach

**Choice**: Use a `useAutoResize` hook that adjusts `textarea.style.height` on input via `scrollHeight`, capped with CSS `max-height`.

**Rationale**: Pure CSS `field-sizing: content` is not yet supported in all browsers. A small hook using `scrollHeight` is the standard approach — no dependencies needed. The hook resets height to `auto` before measuring to handle deletions correctly.

**Max height**: `12rem` (~8 lines). Beyond that, the textarea scrolls. This keeps the page layout stable while giving enough room for longer messages.

### 2. Edit detection via timestamp comparison

**Choice**: Derive "edited" status by comparing `updated_at > created_at` (with a small tolerance of ~1 second to account for auto_now timing). Return `is_edited` as a computed boolean in the API response schemas.

**Alternatives considered**:
- Separate `edited` boolean field: Requires a migration for a value we can already compute. Unnecessary.
- Store `edited_at` timestamp: Over-engineered for current needs — we don't need edit history.

### 3. Edit API endpoint

**Choice**: `PATCH /{project_id}/discussions/{discussion_id}` with `{ body: string }`. Author-only, reuses the same permission pattern as delete.

**Rationale**: PATCH is appropriate since we're partially updating the resource. Reuse existing `NotDiscussionAuthorError` exception for authorization.

### 4. Edit UI pattern

**Choice**: Inline editing — clicking "Edit" replaces the post body with a pre-filled auto-expanding textarea and Save/Cancel buttons. Same component structure as ReplyForm.

**Alternatives considered**:
- Modal dialog: Overkill for a simple text edit, breaks the conversational flow.
- Separate edit page: Unnecessary for single-field edits.

### 5. Shared textarea hook

**Choice**: Extract `useAutoResize` as a shared hook in `src/web-ui/src/hooks/`. Apply it to NewDiscussionForm, ReplyForm, and the new inline edit form.

**Rationale**: All three textareas need the same behavior. A shared hook avoids duplication.

## Risks / Trade-offs

- **scrollHeight measurement on every keystroke** → Negligible performance cost for text inputs of this size. No mitigation needed.
- **No edit window / time limit** → Authors can edit posts at any time. Acceptable for a community tool; revisit if abuse becomes a concern.
- **Edited indicator without history** → Users can see a post was edited but not what changed. This is the standard pattern (used by Slack, Discord, etc.) and sufficient for now.
