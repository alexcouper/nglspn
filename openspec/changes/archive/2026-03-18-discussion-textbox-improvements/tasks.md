## 1. Backend — Edit endpoint and service

- [x] 1.1 Add `update_discussion` to `DiscussionHandlerInterface` with signature `(discussion_id, requesting_user_id, body) -> Discussion`
- [x] 1.2 Implement `update_discussion` in `django_impl/handler.py` — fetch discussion, check author, update body, save, return
- [x] 1.3 Add PATCH endpoint `/{project_id}/discussions/{discussion_id}` to discussions router with author-only permission
- [x] 1.4 Add `is_edited` computed boolean to `DiscussionResponse` and `ReplyResponse` schemas (true when `updated_at` > `created_at` + 1s)
- [x] 1.5 Regenerate OpenAPI spec and TypeScript types (`make extract-openapi` + `npm run generate-types`)

## 2. Frontend — Auto-expanding textarea

- [x] 2.1 Create `useAutoResize` hook in `src/web-ui/src/hooks/` — adjusts textarea height via scrollHeight, capped at `12rem`
- [x] 2.2 Apply `useAutoResize` to `NewDiscussionForm` textarea (keep min 3 rows)
- [x] 2.3 Apply `useAutoResize` to `ReplyForm` textarea (keep min 2 rows)

## 3. Frontend — Edit UI

- [x] 3.1 Add `onEdit` callback prop to `DiscussionList` / `DiscussionItem` / `ReplyItem` and wire up API call in `InlineDiscussions`
- [x] 3.2 Add inline edit mode to `DiscussionItem` — pencil icon button, toggling between body display and edit textarea with Save/Cancel
- [x] 3.3 Add inline edit mode to `ReplyItem` — same pattern as DiscussionItem
- [x] 3.4 Apply `useAutoResize` to inline edit textareas
- [x] 3.5 Display "(edited)" indicator next to timestamp when `is_edited` is true

## 4. Testing and linting

- [x] 4.1 Run backend linting (`make lint`) and fix issues
- [x] 4.2 Run backend tests (`make test`) and fix issues
- [x] 4.3 Run frontend linting (`npm run lint`) and fix issues
- [x] 4.4 Browser test: create a discussion, edit it, verify edited indicator appears and body updates
