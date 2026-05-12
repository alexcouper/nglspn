# RECTIFY — in-app discussion notifications follow-ups

Code-review follow-ups against the `in-app-discussion-notifications` change. Each section is independently executable. **Branches**: do all of this on the same branch the original change lives on (or a follow-up branch off it). The original change is already archived under `openspec/changes/archive/2026-05-06-in-app-discussion-notifications/`.

## Conventions for the executor

- This repo uses **jj** (jujutsu), not git. See user-level CLAUDE.md.
- Backend lives at `src/django-backend/`; web-ui at `src/web-ui/`.
- After backend API changes, regenerate types: `cd src/django-backend && make extract-openapi && cd ../web-ui && npm run generate-types`.
- Run `make lint` + `make test` from `src/django-backend/` after backend work; `npm run lint` from `src/web-ui/` after frontend work.
- Don't add "Generated with Claude Code" or `Co-Authored-By` lines to commits.

---

## 1. `headline_kind` — replace string with enum

**Where**
- `src/django-backend/services/notifications/__init__.py` (dataclass field, currently `headline_kind: str`)
- `src/django-backend/services/notifications/django_impl/handler.py:67-72` (the place strings are produced)
- `src/django-backend/api/schemas/notification.py:34` (response schema)
- `src/web-ui/src/lib/notifications.ts:10-21` (consumer)

**Do**
- Add `class NotificationHeadlineKind(str, Enum)` in `services/notifications/__init__.py` with members `STARTED = "started"` and `REPLIED = "replied"`. `str` mixin keeps JSON serialization stable.
- Change `NotificationGroup.headline_kind` to `NotificationHeadlineKind`.
- In handler, replace `"started"` / `"replied"` literals with the enum.
- In `api/schemas/notification.py`, change the schema field type to the same enum (ninja accepts `Enum`-typed fields and emits OpenAPI `enum: [started, replied]`).
- Regenerate OpenAPI + TS types. The TS type will now be a string-literal union `"started" | "replied"`. Update `buildHeadline` to compare against the literals (already does).

**Acceptance**
- Existing tests pass without changes (string equality still works).
- The generated OpenAPI shows `"enum": ["started", "replied"]` for the `headline_kind` field.
- TS `NotificationGroup["headline_kind"]` is the literal union.

---

## 2. `_root_id` — investigate nesting and fix or restrict

**Context**
The data model (`apps/discussions/models.py:20-26`) defines `parent = FK("self")` with no depth validation. So the schema *allows* replies-of-replies, but:
- Frontend (`InlineDiscussions.tsx`, `DiscussionList.tsx`) and `findCommentInTree` only handle two levels.
- Backend recipient resolution (`services/notifications/django_impl/handler.py:118-120` — `root = discussion.parent if discussion.parent else discussion`) only walks one level.
- `_root_id` (handler.py:42) uses `parent_id or discussion_id` — same.

So today the system is 2-level by accident, not by enforcement. The user wants this to support arbitrary nesting cleanly.

**Decision to make first**
Pick one and document it in the change's design notes:
- **(A) Enforce single-level via validation.** Discussions API rejects creating a reply whose `parent_id` already has a non-null `parent_id`. Cheap, keeps everything else simple. Matches current frontend.
- **(B) Support arbitrary nesting.** Requires the changes below.

If picking (B), implement the following:

**Do (option B only)**
- Add `Discussion.root` denormalized column: `root = FK("self", on_delete=CASCADE, null=True, related_name="thread_descendants", db_index=True)`. Migration sets `root_id = id` for current root rows and `root_id = parent.root_id` (or `parent_id` for one-level-deep replies) for current replies.
- In `services/discussions/django_impl/handler.py:22-34` (the create method), when creating a reply set `root = parent.root or parent` so the column is always populated.
- Replace `_root_id` (`services/notifications/django_impl/handler.py:42`) with reading `notification.discussion.root_id` (with fallback to `discussion_id` for the legacy edge case).
- Replace recipient-root walk (`services/notifications/django_impl/handler.py:118`) with `root = discussion.root if discussion.root_id else discussion`.
- Update `unread_rows_for_thread` (`services/notifications/django_impl/query.py:44-50`) to filter on `Q(discussion__root_id=root_discussion_id) | Q(discussion_id=root_discussion_id)` (the second clause covers the case where `root_discussion_id` is itself a root, where `root_id` is NULL on the root row).
- Update frontend `findCommentInTree` (`src/web-ui/src/components/InlineDiscussions.tsx:18-33`) to recurse through `replies[]` arbitrarily deeply. Currently it only iterates one level.
- Update `DiscussionList.tsx` to render nested replies recursively (current implementation only renders `discussion.replies` flat; nested replies of replies wouldn't show).

**Acceptance (option B)**
- A new test in `services/notifications/django_impl/test_handler.py` creating root → reply → reply-of-reply asserts that all descendants coalesce under the same group with `root_discussion_id == root.id` and `headline_kind == "replied"`.
- A new test asserts `mark_thread_read_for_user(root.id)` clears notifications for the root, the reply, and the nested reply.
- Discussions list UI test (or manual screenshot) shows multi-level nesting.

**Recommendation**
Default to **(A)** unless the user wants nesting now. (A) is one validator + two scenarios in `discussions` spec; (B) is a migration + recursion across two surfaces. The user's question implied they want it to work — confirm before doing (B).

---

## 3. Project image URL — go through the front door

**Where**
- `src/django-backend/services/notifications/django_impl/handler.py:32-39` (currently imports `_variant_url` and `resolve_image_by_purpose` from another service's privates)

**Do**
- Add `get_project_icon_url(project: Project | UUID) -> str | None` to `ProjectQueryInterface` (`src/django-backend/services/project/query_interface.py`).
- Implement it in `DjangoProjectQuery` (`src/django-backend/services/project/django_impl/query.py`). Move/reuse the `resolve_image_by_purpose(project, "icon")` + `_variant_url(image, "thumb")` chain inside it. Keep `_variant_url` private to the project module — only the new public method crosses the boundary.
- In notifications handler, replace `_resolve_project_image_url` with `REPO.project.get_project_icon_url(project)`. Delete the local helper and the cross-module imports.
- If `_variant_url` is also used elsewhere outside the project module, leave those for now (out of scope) but flag in the commit message.

**Acceptance**
- `grep -r "from services.project.django_impl.query import" src/django-backend/services/notifications/` returns nothing.
- Existing notification tests still pass.
- Add a unit test for `REPO.project.get_project_icon_url` that covers: project with icon image, project with no icon, project where the icon has no `thumb` variant (falls back to original URL).

---

## 4. `count_unread_groups_for_user` — push dedup to SQL, with a query-shape test

**Where**
- `src/django-backend/services/notifications/django_impl/query.py:36-42`

**Do**
- Replace the Python-side dedup with a SQL `DISTINCT` over `Coalesce(parent_id, discussion_id)`:
  ```python
  from django.db.models import F
  from django.db.models.functions import Coalesce

  def count_unread_groups_for_user(self, user_id: UUID) -> int:
      return (
          _unread_qs(user_id)
          .annotate(root=Coalesce(F("discussion__parent_id"), F("discussion_id")))
          .values("root")
          .distinct()
          .count()
      )
  ```
- The existing `notifications_recip_inapp_idx` index already supports the WHERE.

**Test (write this BEFORE the implementation change so you can compare)**
- Add `test_count_query_shape` in `src/django-backend/services/notifications/django_impl/test_query.py`:
  ```python
  from django.test.utils import CaptureQueriesContext
  from django.db import connection
  
  def test_count_query_runs_in_one_query_with_distinct(query):
      user = UserFactory()
      project = ProjectFactory()
      root = DiscussionFactory(project=project)
      for _ in range(50):
          DiscussionFactory(project=project, parent=root)  # 50 replies
          NotificationFactory(recipient=user, discussion=...)  # one per reply
      NotificationFactory(recipient=user, discussion=root)
      
      with CaptureQueriesContext(connection) as ctx:
          result = query.count_unread_groups_for_user(user.id)
      
      assert result == 1
      assert len(ctx.captured_queries) == 1
      sql = ctx.captured_queries[0]["sql"].lower()
      assert "distinct" in sql or "group by" in sql, sql
  ```
- Run the test on **current code** to capture the existing SQL string, then again **after** the change to confirm the SQL contains `DISTINCT`/`GROUP BY`. Commit both runs' captured SQL in the commit message body for the reviewer's benefit (or just describe the diff).

**Acceptance**
- New `test_count_query_runs_in_one_query_with_distinct` passes.
- Existing `TestCountUnreadGroupsForUser` tests still pass.

---

## 5. Log the deletion count

**Where**
- `src/django-backend/api/tasks/notifications.py:30-33`

**Do**
```python
@task()
def delete_old_read_notifications() -> None:
    from services import HANDLERS

    deleted = HANDLERS.notifications.delete_old_read_notifications()
    logger.info("delete_old_read_notifications removed %d rows", deleted)
```
Add `import logging` + `logger = logging.getLogger(__name__)` to the module.

**Acceptance**
- The existing `test_delete_old_read_notifications_invokes_handler` still passes.
- Add a follow-up test that asserts the log message is emitted with the count, using `caplog`.

---

## 6. Drop the `_full_name` defensive `hasattr`

**Where**
- `src/django-backend/services/notifications/django_impl/handler.py:46-52`

**Do**
- Replace
  ```python
  full = user.full_name if hasattr(user, "full_name") else None
  ```
  with `full = user.full_name`. `User.full_name` is a stable property (used elsewhere in the codebase, e.g. `services/email/django_impl/handler.py`).
- Verify by grep: `grep -n "full_name" src/django-backend/apps/users/models.py` should show the property defined directly on the model.

**Acceptance**
- Tests still pass; the function output is unchanged.

---

## 7. Inject `HANDLERS` / `REPO` instead of lazy-importing them — bigger refactor

**Goal**
Remove every `from services import HANDLERS` / `from services import REPO` *inside method bodies* across the service layer. Each handler/query holds references to the rest of the service graph and calls `self._handlers.x` / `self._repo.x`.

**Approach: post-construction wiring**

`services/__init__.py`:
```python
@dataclass
class HandlerServices:
    discussions: DiscussionHandlerInterface = field(default_factory=DjangoDiscussionHandler)
    email: EmailHandlerInterface = field(default_factory=DjangoEmailHandler)
    notifications: NotificationHandlerInterface = field(default_factory=DjangoNotificationHandler)
    # ...
    
    def _attach(self, repo: "QueryServices") -> None:
        for handler in (self.discussions, self.email, self.notifications, self.image,
                        self.project, self.registration, self.reviews, self.users):
            handler._handlers = self
            handler._repo = repo

@dataclass
class QueryServices:
    # ... same shape ...
    
    def _attach(self, handlers: "HandlerServices") -> None:
        for query in (self.discussions, self.email, self.notifications, self.project, self.users):
            query._handlers = handlers
            query._repo = self

HANDLERS = HandlerServices()
REPO = QueryServices()
HANDLERS._attach(REPO)
REPO._attach(HANDLERS)
```

Each `Django*Handler` / `Django*Query`:
```python
class DjangoNotificationHandler(NotificationHandlerInterface):
    _handlers: "HandlerServices | None" = None
    _repo: "QueryServices | None" = None
    
    def list_unread_groups_for_user(self, user_id, limit=50):
        rows = list(self._repo.notifications.list_unread_for_user(user_id))
        # ...
```

**Migration steps**
1. Add `_handlers` / `_repo` class attributes (`= None`) to every `Django*Handler` and `Django*Query`.
2. Add the two `_attach` methods + the wiring lines in `services/__init__.py`.
3. For each `from services import HANDLERS` / `from services import REPO` inside a method body, replace with `self._handlers` / `self._repo` and remove the import line.
4. Use `grep -rn "from services import" src/django-backend/services/` to verify no lazy imports remain inside the service tree.

**Test impact**
- Many tests construct `DjangoNotificationHandler()` directly (e.g. `test_handler.py`, `test_in_app.py`). Under the new wiring, those instances have `_handlers = None` / `_repo = None` until attached.
- Two options:
  - **Option a**: Keep a small fallback at the access site:
    ```python
    @property
    def repo(self):
        if self._repo is None:
            from services import REPO
            return REPO
        return self._repo
    ```
    This still imports lazily but only as a fallback for unwired test instances. Production paths (which go through `HANDLERS.x`) skip the fallback. This is the lightest-touch change.
  - **Option b**: Update tests to use the wired global: `from services import HANDLERS; handler = HANDLERS.notifications`. Cleaner long-term but touches every service test. Defer to follow-up unless the user wants it now.

**Recommendation**
Do **Option (a)**. The point of the refactor is to clean up production paths, not to rewrite every test fixture. Once production code uses `self._handlers`/`self._repo`, the lazy-import fallback can be removed in a later pass.

**Acceptance**
- `grep -rn "from services import HANDLERS\|from services import REPO" src/django-backend/services/` returns zero hits inside method bodies (top-of-module type-only imports under `TYPE_CHECKING` are fine).
- All existing tests pass.

---

## 8. Extract `<NotificationGroupItem>` — share rendering across popover, feed, toaster

**Where (currently duplicated)**
- `src/web-ui/src/components/NotificationsBell.tsx:100-124` (popover row, wraps in `<Link>`)
- `src/web-ui/src/app/notifications/NotificationsFeed.tsx:98-136` (feed row, has checkbox + unread-count suffix)
- `src/web-ui/src/components/NotificationToaster.tsx:64-103` (toast card, has dismiss button)

**Do**
- Create `src/web-ui/src/components/NotificationGroupItem.tsx` exporting:
  ```tsx
  type Variant = "popover" | "feed" | "toaster";
  
  interface Props {
    group: NotificationGroup;
    variant: Variant;
    showUnreadSuffix?: boolean;  // feed only — adds " · N unread"
  }
  
  export function NotificationGroupItem({ group, variant, showUnreadSuffix }: Props) {
    // renders icon + headline + body excerpt + (optional) timestamp + (optional) unread suffix
    // sizes: popover/toaster use 36-40px icon; feed uses 48px
  }
  ```
- Refactor the three call sites to use it. The surrounding chrome differs:
  - Popover: wraps in `<Link>` — the link wrapping happens *outside* the component.
  - Feed: renders checkbox to the left, wraps the row in `<Link>`.
  - Toaster: renders inside the toast card, with a dismiss button alongside.
- Don't move `Link` rendering into the component — keep the wrapper outside so callers control click semantics (toaster does `router.push` programmatically; feed/popover use `<Link>`).
- Move `relativeTime` rendering inside the component, gated by variant (toaster doesn't show it; popover and feed do).

**Acceptance**
- Visual diff (manual): popover, feed, and toaster look the same as before.
- `grep -n "buildHeadline\|latest_body_excerpt" src/web-ui/src/components/NotificationsBell.tsx src/web-ui/src/app/notifications/NotificationsFeed.tsx src/web-ui/src/components/NotificationToaster.tsx` shows each file references them at most once (or not at all if fully delegated).

---

## 9. Unify the two toast UIs

**Context**
- `NotificationToaster.tsx` is a fixed-position bottom-right floating card for new arrivals.
- `InlineDiscussions.tsx:224-231` renders an inline amber banner above the form for "this discussion is no longer available." Different shape, different placement, different code path.

**Do**
- Introduce a tiny global toast primitive. Two acceptable shapes:
  - **(A) A `ToastContext` + `useToast()` hook** (`src/web-ui/src/contexts/toasts.tsx`):
    ```tsx
    type ToastKind = "info" | "warning" | "error";
    interface Toast { id: string; kind: ToastKind; title: string; description?: string; ttlMs?: number; onClick?: () => void; }
    const { showToast } = useToast();
    showToast({ kind: "warning", title: "This discussion is no longer available." });
    ```
    Renders a single fixed-position container at the root layout that displays whatever's in the queue.
  - **(B) Convert `NotificationToaster` into a generic `Toaster` and have it pull from a global queue** (lighter touch).

  Pick **(A)** — clearer separation of concerns and the existing `NotificationToaster` becomes a *consumer* of `useToast` rather than a bespoke surface.
- Mount the new `<ToastContainer />` in `src/web-ui/src/app/layout.tsx` next to where `NotificationToaster` lives (or replace `NotificationToaster` outright).
- Refactor `NotificationToaster` to call `showToast` from its `subscribeDiff` listener instead of managing its own `toasts` state. Each toast renders with the existing `<NotificationGroupItem variant="toaster" />` (post Item 8).
- Refactor `InlineDiscussions.tsx` to drop the inline `staleToast` state and call `showToast({ kind: "warning", title: "This discussion is no longer available." })` instead.
- Remove the inline amber banner JSX (`InlineDiscussions.tsx:224-231`) and the `staleToast` `useState`.

**Acceptance**
- `grep -rn "staleToast" src/web-ui/src/` returns zero hits.
- Manually trigger both surfaces and confirm both render through the same toast container.
- `NotificationToaster.tsx` no longer manages a `useState<ActiveToast[]>` — it's a thin diff listener.

---

## 10. Hide the bell during onboarding on both viewports

**Where**
- `src/web-ui/src/components/Navigation.tsx:84` (desktop, currently `isAuthenticated` only)
- `src/web-ui/src/components/Navigation.tsx:102` (mobile, already `isAuthenticated && hasCompletedOnboarding`)

**Do**
- Change desktop conditional to gate on both flags too:
  ```tsx
  {hasCompletedOnboarding && <NotificationsBell />}
  ```
- The `<UserMenu />` next to it should keep its current visibility behavior.

**Acceptance**
- Manual: log in as a user mid-onboarding (or in `?onboarding=true` mode). The bell should not appear in either viewport.
- Existing post-onboarding behavior unchanged.

---

## 11. Remove the unread badge from the Discussions tab

**Where**
- `src/web-ui/src/app/projects/[slug]/ProjectDetailContent.tsx:19` (import of `useNotifications`)
- `src/web-ui/src/app/projects/[slug]/ProjectDetailContent.tsx:29-36` (`unreadDiscussionCount` useMemo)
- `src/web-ui/src/app/projects/[slug]/ProjectDetailContent.tsx:232-243` (the badge JSX inside the tab label)

**Why**
The badge tells the user "there are unread comments" while the tab content does not show those comments live — they only appear after navigating away and back, which is confusing. Rather than add liveness, drop the per-page indicator. The top-bar dot is the single live signal.

**Do**
- Remove the `useNotifications` import and the `unreadDiscussionCount` `useMemo`.
- Replace the tab definition's `label` with the plain string `"Discussions"`.
- Verify nothing else in `ProjectDetailContent.tsx` references `unreadGroups`.

**Acceptance**
- The Discussions tab label is plain text.
- No tests reference `unreadDiscussionCount`.
- Manual: with unread notifications for a project, the project page tab is unchanged; the top-bar bell still shows the dot.

---

## 12. New endpoint: `mark-all-read`

**Backend**

`src/django-backend/services/notifications/handler_interface.py`: add
```python
@abstractmethod
def mark_all_read_for_user(self, user_id: UUID) -> int: ...
```

`src/django-backend/services/notifications/django_impl/handler.py`: add
```python
def mark_all_read_for_user(self, user_id: UUID) -> int:
    return Notification.objects.filter(
        recipient_id=user_id, in_app_read_at__isnull=True
    ).update(in_app_read_at=timezone.now())
```

`src/django-backend/api/schemas/notification.py`: add
```python
class MarkAllReadResponse(Schema):
    marked: int
```

`src/django-backend/api/routers/notifications.py`: add
```python
@router.post("/mark-all-read", response={200: MarkAllReadResponse}, auth=auth, tags=["Notifications"])
def mark_all_read(request: HttpRequest) -> MarkAllReadResponse:
    marked = HANDLERS.notifications.mark_all_read_for_user(request.auth.id)
    return MarkAllReadResponse(marked=marked)
```

**Tests**
- Service test in `services/notifications/django_impl/test_in_app.py`: marks all unread rows for the calling user, ignores other users, idempotent (returns 0 on second call).
- API test in `api/routers/test_notifications.py`: 401 unauth, 200 + correct count, doesn't touch other users.

**Spec update**
- Add a new requirement section to `openspec/specs/notifications/spec.md` — "Mark all read endpoint" — mirroring the shape of the existing "Mark thread read endpoint" requirement, with two scenarios (some unread / no unread).

**Frontend**
- `src/web-ui/src/lib/api/notifications.ts`: add `markAllRead(): Promise<{ marked: number }>` calling `POST /api/notifications/mark-all-read`.
- `src/web-ui/src/contexts/notifications.tsx`: add `markAllRead` to the context, mirroring `markThreadRead` (calls API once, then `refreshSummary`).
- `src/web-ui/src/app/notifications/NotificationsFeed.tsx:50-62`: replace the `Promise.all(groups.map(g => markThreadRead(...)))` loop with a single `markAllRead()` call.

**OpenAPI regen**
- `cd src/django-backend && make extract-openapi && cd ../web-ui && npm run generate-types`.

**Acceptance**
- New service + API tests pass.
- "Mark all as read" on the `/notifications` page issues exactly one API request (verify in DevTools Network or with a test).

---

## 13. `mark-thread-read` accepts `comment_id` as fallback

**Goal**
Stop using a comment id as a `root_discussion_id`. Allow either field; backend resolves comment → root.

**Backend**

`src/django-backend/api/schemas/notification.py`: change `MarkThreadReadRequest`:
```python
class MarkThreadReadRequest(Schema):
    root_discussion_id: UUID | None = None
    comment_id: UUID | None = None

    @model_validator(mode="after")
    def exactly_one(self) -> "MarkThreadReadRequest":
        provided = sum(x is not None for x in (self.root_discussion_id, self.comment_id))
        if provided != 1:
            raise ValueError("exactly one of root_discussion_id or comment_id is required")
        return self
```
(ninja uses pydantic validators — confirm import path: `from pydantic import model_validator`.)

`src/django-backend/services/notifications/handler_interface.py`: add
```python
@abstractmethod
def mark_thread_read_for_comment(self, user_id: UUID, comment_id: UUID) -> int: ...
```

`src/django-backend/services/notifications/django_impl/handler.py`: add
```python
def mark_thread_read_for_comment(self, user_id: UUID, comment_id: UUID) -> int:
    try:
        d = Discussion.objects.values("id", "parent_id").get(id=comment_id)
    except Discussion.DoesNotExist:
        return 0
    root_id = d["parent_id"] or d["id"]
    return self.mark_thread_read_for_user(user_id, root_id)
```

If Item 2 option B is implemented (denormalized `root` column), use `d["root_id"] or d["id"]` instead.

`src/django-backend/api/routers/notifications.py`: route the call:
```python
def mark_thread_read(request, payload):
    if payload.root_discussion_id is not None:
        marked = HANDLERS.notifications.mark_thread_read_for_user(request.auth.id, payload.root_discussion_id)
    else:
        marked = HANDLERS.notifications.mark_thread_read_for_comment(request.auth.id, payload.comment_id)
    return MarkThreadReadResponse(marked=marked)
```

**Tests**
- Service test for `mark_thread_read_for_comment`: comment is a reply → marks all thread rows; comment is a root → marks all thread rows; comment doesn't exist → returns 0.
- API test: pass `comment_id` only and verify it works; pass both → 422; pass neither → 422.

**Spec update**
- Update the "Mark thread read endpoint" requirement in `openspec/specs/notifications/spec.md` to describe the one-of body and add a scenario "Marks thread when only comment id is known" (covers the deleted-discussion fallback).

**Frontend**

`src/web-ui/src/lib/api/notifications.ts`:
```ts
async markThreadRead(rootDiscussionId: string): Promise<{ marked: number }> { ... }  // unchanged

async markThreadByComment(commentId: string): Promise<{ marked: number }> {
  return this.client.request("/api/notifications/mark-thread-read", {
    method: "POST",
    body: JSON.stringify({ comment_id: commentId }),
  });
}
```

`src/web-ui/src/contexts/notifications.tsx`: add `markThreadByComment` to the context, same shape as `markThreadRead`.

`src/web-ui/src/components/InlineDiscussions.tsx:122-123`: replace the bare-comment-id case:
```ts
// before:
void markThreadRead(commentParam);
// after:
void markThreadByComment(commentParam);
```

**OpenAPI regen** as above.

**Acceptance**
- The frontend never passes a comment id labelled as `root_discussion_id`. `grep -n "root_discussion_id" src/web-ui/src/` shows only legitimate root-id usages.
- New tests pass.
- Spec scenario covers the comment-id-only path.

---

## Order of execution (suggested)

The user can pick any order, but if executing top-to-bottom this minimizes merge churn:

1. **Quick backend wins** — Items 5, 6, 1 (small, isolated)
2. **Backend correctness** — Items 3, 4 (bounded; Item 4 includes the test-first capture)
3. **Decide Item 2** — confirm A vs B with the user before implementing B
4. **Backend feature additions** — Items 12, 13 (each ships a new endpoint + spec update + types regen)
5. **Backend DI refactor** — Item 7 (touches every Django*Handler/Query — do after the other backend items so its diff stays focused)
6. **Frontend extraction** — Item 8 (lays groundwork for 9)
7. **Frontend unification** — Items 9, 10, 11 (parallel-safe; 11 is independent)

After each item: `make ci` (or at minimum `make lint && make test` in `src/django-backend/` for backend items, `npm run lint` in `src/web-ui/` for frontend items).

---

## Out of scope for this rectify pass

These were raised in review but explicitly NOT in this plan:
- Cross-tab toaster deduplication (design decision, deferred per design.md).
- WebSocket / SSE delivery (deferred per design.md).
- The synced UI spec's `Purpose: TBD` placeholder — fix opportunistically when next editing that file.
- Untracked `gulrót-*.jpg` / `sellerí-*.jpg` trophy images in `src/web-ui/public/trophies/` — unrelated to this change.

---

## Completion status (2026-05-11)

Each completed item is one jj changeset stacked on the RECTIFY commit (`kqun b56f`). Order reflects the suggested execution order, not item number.

### Done

| Item | Subject | Changeset description |
|------|---------|------------------------|
| 5 | log delete count | `rectify item 5: log delete_old_read_notifications row count` |
| 6 | drop hasattr full_name | `rectify item 6: drop defensive hasattr full_name guard` |
| 1 | NotificationHeadlineKind enum | `rectify item 1: NotificationHeadlineKind enum` |
| 3 | get_project_icon_url through ProjectQueryInterface | `rectify item 3: get_project_icon_url through ProjectQueryInterface` |
| 4 | count dedup pushed to SQL | `rectify item 4: push count dedup to SQL via DISTINCT COALESCE(parent_id, discussion_id)` |
| 2 | enforce single-level nesting (option **A**) | `rectify item 2A: enforce single-level discussion nesting` |
| 12 | mark-all-read endpoint | `rectify item 12: mark-all-read endpoint` |
| 13 | mark-thread-read accepts comment_id | `rectify item 13: mark-thread-read accepts comment_id` |
| 8 | extract `<NotificationGroupItem>` | `rectify item 8: extract NotificationGroupItem` |
| 9 | unify toast UIs via `ToastContext` | `rectify item 9: unify toast UIs via ToastContext` |
| 10 | hide bell during onboarding (desktop) | `rectify item 10: hide bell during onboarding on desktop` |
| 11 | remove unread badge from Discussions tab | `rectify item 11: remove unread badge from Discussions tab` |

### Not done

- **Item 7 — DI refactor (`from services import HANDLERS/REPO` removal).** Deferred to a follow-up change on the user's instruction. Production code still uses lazy module-level imports; nothing else in the codebase depends on the proposed `_attach`/`_handlers`/`_repo` shape.
- **Item 2 option B (denormalized `Discussion.root` column + arbitrary nesting).** Not chosen. Option A enforces single-level via a server-side validator on the reply create endpoint and adds a 422 path; frontend code remains 2-level by accident as before.

### What was tested

- **Backend:** Full pytest suite green at the end of the pass: 647 passed (~2m40s), no failures. Per-item, the relevant subset was run after each change (notifications, discussions, project query, tasks).
- **Backend lint:** `make lint` (ruff check + format) passes with zero issues at the tip of the stack.
- **Backend new tests added:** caplog assertion on `delete_old_read_notifications` log line; `get_project_icon_url` (4 cases inc. fallback to original URL when no thumb variant); `count_unread_groups_for_user` query-shape (CaptureQueriesContext, asserts single query containing `distinct`/`group by`); reply-of-reply 422; `mark_all_read_for_user` (3 cases) + API tests (auth, marks all, scoped to caller); `mark_thread_read_for_comment` (reply, root, missing) + API tests (comment-only, both-fields-rejected, neither-rejected).
- **Backend SQL change captured:** Item 4 — old SQL pulled `(discussion_id, parent_id)` for every unread row and deduped in Python; new SQL is `SELECT COUNT(*) FROM (SELECT DISTINCT COALESCE("discussions"."parent_id", "notifications"."discussion_id") AS "root" FROM "notifications" INNER JOIN "discussions" ON ... WHERE in_app_read_at IS NULL AND recipient_id = ?) subquery`.
- **OpenAPI / TS types regenerated** after items 1, 12, 13. The new `NotificationHeadlineKind` shows up as `enum: ["started","replied"]` in `backend-openapi.json` and as the literal union `"started" | "replied"` in `src/lib/api-types.ts`.
- **Frontend type-check:** `npx tsc --noEmit` is clean for the rectify changes. The four pre-existing `Cannot find module 'vitest'` errors (`src/lib/api/base.test.ts`, `src/test/helpers.ts`, `src/test/setup.ts`, `vitest.config.ts`) are unrelated to this work.
- **Frontend eslint:** `npx eslint .` returns 0 errors. The two pre-existing warnings (unused `reset` in `src/app/projects/error.tsx`) are unrelated.
- **Spec updates:** `openspec/specs/discussions/spec.md` (new "Reply to a reply is rejected" scenario + sentence in the threaded-replies requirement); `openspec/specs/notifications/spec.md` (mark-thread-read body now one-of root_discussion_id|comment_id; new "Marks thread when only comment id is known" + "Rejects request with both fields or neither field" scenarios; new "Mark all read endpoint" requirement with two scenarios).

### What was NOT tested

- **No browser / Playwright verification.** Items 9, 10, and 11 list manual visual checks in their acceptance criteria; none were run. Specifically untested:
  - Item 9: that the toaster floating card and the "discussion no longer available" warning render through the same `<ToastContainer>` mounted in `src/app/layout.tsx` and look acceptable side-by-side.
  - Item 10: that the bell is actually hidden for a desktop user in onboarding (only the conditional was changed and read).
  - Item 11: that the project page Discussions tab now shows plain text and the top-bar bell still shows the dot for the same project.
- **No end-to-end run** of the new `POST /api/notifications/mark-all-read` from the `/notifications` page in a real browser. The unit + API tests cover the contract; the "exactly one API request" check from Item 12's acceptance was not done in DevTools.
- **No Playwright / e2e suite run.** The repo has Playwright wiring but it was not exercised.
