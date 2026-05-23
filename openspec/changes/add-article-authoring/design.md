## Context

Phases 1 and 2 (changes `add-project-following` and `add-follow-preferences-ui`) put the data and UI for per-project, per-channel notification preferences in place but kept the legacy Naglasúpan email pipeline intact. Today, two `User` fields — `email_opt_in_competition_results` and `email_opt_in_platform_updates` — still drive every outbound email to subscribers, and a "mirror" layer copies UI changes back onto those fields so the legacy pipeline stays consistent.

Phase 3 introduces the first publishing surface (Articles), makes the publish event the trigger for notifications (both email and in-app), and uses that opportunity to retire the legacy flags. The `Notification` model — until now anchored to a `Discussion` — must learn to point at an `Article` too. The `async-broadcast-send` pipeline — until now resolving recipients via the legacy flags — must consult Follow + per-channel email switches on the Naglasúpan house project.

Stakeholders: project owners (new authoring affordance), Naglasúpan admins (channel management, content backfill plumbing), every existing subscriber (the no-regression contract: nobody starts or stops receiving emails because of this change).

## Goals / Non-Goals

**Goals:**
- A working internal authoring flow: draft → publish → notification fan-out.
- A single, generalised notification path that handles both discussion and article events, gated by the user's per-channel preferences.
- Complete removal of the legacy `email_opt_in_*` fields and the mirror logic that kept them in sync.
- No subscriber-visible regression: anyone receiving Naglasúpan emails today continues to receive them; anyone opted out continues to be opted out.
- Forward-compatible Article model: columns `source` and `external_url` exist from day one so Phase 6 (RSS ingestion) doesn't require another model migration.
- Forward-compatible approval flow: the `article_trust` flag governs internal authors today and Phase 6 will route external feeds through the same approval surface.

**Non-Goals:**
- `/news` page, project-page News carousel, Discover News carousel — Phase 5.
- External RSS ingestion, per-feed approval queue — Phase 6.
- Historical content backfill — Phase 4 (content op, no code).
- Profile-side article authoring, per-user RSS feeds, following users — out of scope for v1 (depends on user slugs).
- Per-article comments — the existing project-level discussion thread continues to serve discussion.
- In-platform reader for external articles (they open in a new tab to source URL).
- Per-channel cadence (cadence stays user-global via existing `notification_frequency`).

## Decisions

### 1. Generalise `Notification` with nullable `discussion` + nullable `article` FKs

`apps/notifications/models.py:Notification` currently has a non-null `discussion = FK(Discussion)` and a unique constraint on `(recipient, discussion)`. Phase 3 needs the same row to (alternatively) point at an `Article`.

**Decision:** make `discussion` nullable, add a nullable `article = FK(Article)`, and enforce "exactly one is set" via a Postgres CHECK constraint (`(discussion_id IS NULL) != (article_id IS NULL)`) plus a save-time guard for SQLite. Replace the single unique constraint with two partial unique constraints: `(recipient, discussion)` where discussion is not null, and `(recipient, article)` where article is not null.

**Alternatives considered:**
- Separate `ArticleNotification` model — would duplicate the cadence/email_sent/in_app_read_at columns and force the in-app UI layer to query two tables and merge them. Rejected: doubles read-path complexity for a small write-side simplification.
- Generic FK (`content_type` + `object_id`) — works but loses FK integrity, complicates admin and DRF/Ninja serialisation, and is harder for future analytics. Rejected: the polymorphism is only two-wide and unlikely to grow further.

The nullable-pair approach keeps `recipient`, `email_cadence`, `email_sent`, `email_sent_at`, `in_app_read_at`, `created_at` exactly as they are. Callers that filter `.notifications.filter(in_app_read_at__isnull=True)` keep working.

### 1a. All article + channel access goes through a service layer (no ORM in routes)

This codebase already enforces a handler/repository pattern for cross-cutting domains (`services/notifications/`, `services/follows/`, `services/email/`, etc.) — API routes are thin pass-throughs that call `HANDLERS.<domain>.<verb>` or `REPO.<domain>.<read>`, and never touch ORM managers directly. The `notifications` spec is explicit about this ("SHALL be implemented in the API layer as a thin pass-through to `HANDLERS.notifications.*` and SHALL NOT access ORM models directly").

**Decision:** create `services/articles/` (handler + repo + django_impl), register it as `HANDLERS.articles` / `REPO.articles` in `services/__init__.py`, and put all article business logic — draft creation, update, publish (including slug generation + visibility decision + notification trigger), delete, admin demote — inside the handler. Route handlers in `api/routers/articles.py` are thin pass-throughs that parse the request body, run the `full_edit` permission check, call exactly one handler/repo method, and shape the response.

The same applies to channel management. The simplest wiring is to add channel operations to the same `HANDLERS.articles` handler (channels are tightly bound to articles in this change and a separate handler would be one verb each); the alternative is `HANDLERS.channels` as its own surface. **Default:** put channel CRUD on `HANDLERS.articles` (`add_channel`, `rename_channel`, `delete_channel`, `bulk_reassign_articles`) — the operations are small and they share repository read-paths with article queries. Revisit if `channels` grows independent concerns (e.g. Phase 6 feed-pinning).

**Why:** consistency with the rest of the backend (every existing capability that crosses HTTP + DB does this), testability (handlers are unit-testable without spinning up the API layer), and a single chokepoint for transaction boundaries, signal interaction, and permission enforcement.

**Alternatives considered:**
- Direct ORM in the route handlers — fast to write but breaks the established pattern, splits business logic across HTTP + DB layers, makes it hard to test the publish workflow without going through the request cycle.
- Django signals (`post_save` on Article) instead of an explicit publish handler — too implicit for a workflow with branching behaviour (trust check, backdate suppression, notification fan-out); signals are right for "Channel auto-created on Project save" but wrong for a multi-step publish.

### 2. Article model lives in a new `apps/articles` Django app

`Article` doesn't belong inside `apps/projects` (the project app is already large and articles have their own lifecycle, admin surface, and tests). It doesn't belong inside `apps/notifications` either (the notification is downstream of the article event). A dedicated `apps/articles` app keeps boundaries clean and follows the codebase convention (compare `apps/discussions`).

Channel already lives in `apps/projects` (added by `add-project-following`). It stays there — articles import from it via FK.

Fields (subject to migration-time refinement):

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | primary key, matches house style |
| `project` | FK Project | `on_delete=CASCADE`, `related_name="articles"` |
| `channel` | FK Channel | `on_delete=PROTECT` so a channel with articles can't be silently deleted |
| `author` | FK User | nullable; null when `source = external` |
| `title` | CharField(200) | required |
| `body` | TextField | markdown; required at publish, not at draft |
| `hero_image` | ImageField | required at publish, not at draft; reuses project-image upload pipeline |
| `slug` | SlugField | nullable; assigned on publish for internal articles, never assigned for external |
| `source` | CharField, choices=("internal","external") | default `internal` |
| `external_url` | URLField | nullable; required + set when `source = external` |
| `state` | CharField, choices=("draft","published") | default `draft` |
| `published_at` | DateTimeField | nullable; set on publish; author-settable (allows backdating) |
| `global_visibility` | CharField, choices=("auto","pending","demoted") | default `auto`; see Decision 4 |
| `created_at`, `updated_at` | auto | standard |

Constraints:
- `unique_together("project", "slug")` partial, where slug is not null.
- CHECK: `state = 'draft' OR (title <> '' AND body <> '' AND hero_image <> '')` (deferred to app-layer validation if the CHECK is awkward on SQLite).
- CHECK: `(source = 'internal' AND external_url IS NULL) OR (source = 'external' AND external_url IS NOT NULL)`.

### 3. Backdated publish skips notification fan-out

The publish action accepts an optional `published_at` parameter. Behaviour at publish time:

```
backdate_threshold = now() - 60 seconds
is_backdated = published_at < backdate_threshold
if not is_backdated:
    fan_out_notifications(article)
```

The 60-second skew window absorbs slow clicks, slow saves, and minor clock drift on the API server. Outside that, an author setting `published_at` deliberately into the past gets the "silent publish" behaviour Phase 4's content backfill depends on.

**Alternatives considered:**
- Explicit `silent: bool` parameter on publish — clearer intent but adds another flag, and the natural mental model ("I'm recording something that happened before now") matches the `published_at` semantics anyway. Rejected on the principle of fewer knobs.
- Skip fan-out when `published_at < created_at` — works but ties two timestamps together in a way that breaks if we later support drafts that sit for hours; the absolute-time check is robust to that.

Editing `published_at` after publish (e.g. to fix a typo in the date) **never** fires retroactive notifications. Notification fan-out is a publish-time decision, not a recurring check.

### 4. Approval flow uses `Article.global_visibility` + `User.article_trust`

`User.article_trust = BooleanField(default=True)`. Admin-toggleable.

`Article.global_visibility = CharField(choices=("auto","pending","demoted"), default="auto")`. On publish:
- If `source = internal` and `author.article_trust = True` → `global_visibility = auto`.
- If `source = internal` and `author.article_trust = False` → `global_visibility = pending`.
- (External articles in Phase 6 will land in `pending` until the feed itself is approved.)

Helper property `Article.is_globally_visible` returns `True` iff `state = published` AND `global_visibility = auto`. Local rendering (the project-page Latest News carousel, Phase 5) ignores `global_visibility` — anything published renders on its own project page.

Admin can flip `global_visibility` to `demoted` at any time, which removes the article from global surfaces but leaves the row intact and local rendering unaffected. Admin can also flip a pending article to `auto` to approve it.

The trust flag governs **future** publishes by that user. Flipping `article_trust` from `True` to `False` does not retroactively change `global_visibility` on already-published articles. (Admins who want to pull existing articles use the per-article demote.)

### 5. Notification fan-out implementation

A new function in `services/notifications/` — `notify_article_published(article)` — invoked from the publish path. Publishing itself runs inside `HANDLERS.articles.publish(article_id, published_at=None)`; the publish handler calls `HANDLERS.notifications.create_notifications_for_article(article.id)` on the success branch (matching the discussion-creation pattern already in `services/notifications/`). API route handlers do not invoke the notification handler directly — they only call `HANDLERS.articles.publish`.

Pseudocode:

```python
def notify_article_published(article: Article) -> None:
    if article.state != "published":
        return
    if _is_backdated(article.published_at):
        return
    follows = Follow.objects.filter(project=article.project).select_related("user")
    for follow in follows:
        pref = ChannelPreference.objects.get(follow=follow, channel=article.channel)
        if pref.in_app:
            Notification.objects.create(
                recipient=follow.user,
                article=article,
                email_cadence=follow.user.notification_frequency,
            )
        if pref.email and follow.user.notification_frequency != NotificationCadence.NEVER:
            enqueue_email(follow.user, article)
```

Cadence semantics carry over identically from the discussion path: `IMMEDIATE` → immediate email; `HOURLY` / `DAILY` → digest task picks the row up; `NEVER` → in-app only.

A user can both have `in_app = on` and `email = off` on a channel — they get an in-app notification but no email. The reverse is also valid.

Notification email template for articles: a new template under `templates/emails/` mirroring the discussion template. Subject: "New article in <Project>: <Title>". Body links to the article page.

### 6. Send-path flip in `async-broadcast-send`

The existing `async-broadcast-send` pipeline currently resolves recipients by querying `User.objects.filter(email_opt_in_competition_results=True)` (or `_platform_updates`). This query is replaced with a join: find the Naglasúpan house project, find its "Competition Winners" (or "Product Updates") channel, return `User` rows where a `Follow` exists for that project and a `ChannelPreference` exists for that channel with `email=True`.

This change ships **in the same migration / release** as dropping the legacy `email_opt_in_*` fields. There is no read-the-legacy-field code path remaining after this change.

### 7. Drop legacy fields and remove mirror

Migration sequence inside this change:

1. Add new tables / columns: `Article`, `User.article_trust`, `Notification.article` (nullable), drop NOT NULL from `Notification.discussion`, swap constraints.
2. Update `async-broadcast-send` recipient queries to use the new path.
3. Update `User` admin and `api/schemas/user.py` to remove the legacy fields.
4. Remove the mirror code in `services/project-following/` (the bit that copies UI changes back into `email_opt_in_*`).
5. Drop the legacy columns from `User`.

Each step is a separate migration / commit but they ship together. Rollback strategy: any step is independently revertible up to step 5 (column drop is destructive; after that, restoring requires reading the values back from Follow + preferences — which is exact, because Phase 1's seed migration preserved them).

### 8. Channel management UI

A new "Channels" section in project settings (`/projects/<slug>/settings/channels` or a tab within existing project edit). Operations:

- **Add**: free-form name, validated unique within the project (uniqueness already enforced at DB level by the `(project, name)` constraint added in Phase 1).
- **Rename**: in-place; preferences (FK'd to Channel row, not name) follow the rename transparently.
- **Delete**: rejected by the API if the channel has articles, with a 409 response listing the article count. UI surfaces a "Reassign articles" prompt. v1 keeps the reassignment simple: bulk-set all articles in the channel to a chosen target channel, then delete. (Phase 2's "Updates" channel cannot be deleted if it is the only channel — guard at the API level.)

### 9. Authoring page UX

- Route: `/projects/<slug>/articles/new` (Next.js page); `/projects/<slug>/articles/<id>/edit` for an existing draft.
- Markdown editor with side-by-side preview on ≥ md viewport, tabbed (Edit / Preview) on smaller.
- Drag-to-insert: dropping an image on the editor uploads it via the existing project-image upload endpoint and inserts a `![](url)` at the cursor.
- Hero image: a separate uploader above the body (not part of the markdown body).
- Channel: dropdown of this project's channels.
- Two primary actions: "Save draft" (any state, no requirements), "Publish" (requires title, body, hero image; opens a confirm dialog with optional `published_at` override).

### 10. Article render page

- Route: `/projects/<project-slug>/articles/<article-slug>`.
- Reuses the project-page header so the article is unambiguously part of its project.
- Hero image at the top, title, optional byline, then the markdown-rendered body.
- Returns 404 if `state != published` for anyone but the author + project contributors with `full_edit`.
- Globally-not-visible articles (`global_visibility != auto`) still render on this URL — local rendering is unaffected. The /news + carousel surfaces (Phase 5) are what gate on `is_globally_visible`.
- Internal articles linked from carousels (Phase 5) open in a new tab — `target="_blank"` on the carousel link, matching the "external + internal are equals" framing in the design doc.

## Risks / Trade-offs

- **Notification-storm on first publish after backfill** → mitigated by Phase 4 being a backdated-publish operation; the no-fan-out behaviour at backdate time is now load-bearing and tested.
- **Send-path flip causes a subscriber to silently stop receiving emails** → mitigated by Phase 1's data migration having seeded preferences from the legacy flags. A regression test against a snapshot of "users who would have received the next broadcast pre-flip" vs. "post-flip" gives confidence at deploy time. (Concretely: a management command that diffs the two recipient sets, run against a prod snapshot just before the cutover.)
- **`Notification` constraint change is destructive** → adding the nullable column and the new partial unique constraint is safe; dropping the old `(recipient, discussion)` unique constraint and the NOT NULL on `discussion` must happen in one migration block to avoid an inconsistent intermediate state.
- **Channel delete with reassignment is a heavyweight UI** → v1 keeps it minimal (bulk reassign to one target channel, then delete). If owners want finer-grained per-article moves they edit articles individually, which is supported by the existing channel-on-article dropdown in the edit page.
- **Slug collisions across edits** → slug is generated once on first publish and not regenerated on title edit. Editing the title does not change the URL. Documented in the spec scenarios.
- **`article_trust` UX is invisible to users** → there's no user-facing surface for trust state; it's an admin lever. This is by design (we don't want to discourage authoring), but means trust-false authors may be surprised their article isn't reaching `/news`. Phase 5 will surface a "pending admin approval" badge on the author's own project-page view of the article.
- **Backdated-publish abuse** → a malicious author could backdate to suppress notifications for a real new article. Mitigation: backdate is currently allowed for any `full_edit` contributor (matching the trust model); if it becomes a problem, restrict backdating to admins. Not pre-emptively gating in v1.

## Migration Plan

Single change, multi-step migrations applied in order. Each step is its own Django migration so it can be inspected in isolation.

1. `articles/0001_initial` — create `Article` table with all columns and constraints.
2. `users/000N_add_article_trust` — add `User.article_trust` with `default=True`.
3. `notifications/000N_add_article_fk_and_swap_constraints`:
   - Add nullable `Notification.article = FK(Article)`.
   - Drop NOT NULL on `Notification.discussion`.
   - Drop `(recipient, discussion)` unique constraint.
   - Add partial unique constraint on `(recipient, discussion)` where discussion is not null.
   - Add partial unique constraint on `(recipient, article)` where article is not null.
   - Add CHECK: exactly one of (discussion, article) is set.
4. Code: introduce `services/articles/` with publish + notification fan-out, `apps/articles/admin.py`, API routers, OpenAPI extract, web-ui type regen, authoring + render Next.js pages, channel-management UI.
5. Code: rewrite `async-broadcast-send` recipient resolution to use Follow + per-channel email switches on the house project.
6. Code: remove mirror logic in `services/project-following/` and corresponding test scenarios.
7. `users/000N_drop_email_opt_in_fields` — drop `email_opt_in_competition_results` and `email_opt_in_platform_updates`.
8. Code: remove the two fields from `api/schemas/user.py`, `apps/accounts/` user admin, factories, and tests.

Rollback: steps 1–6 are independently revertible. Step 7 (column drop) is destructive but the values are derivable from the now-canonical Follow + ChannelPreference data, so a recovery migration is mechanical.

Deploy order: a single deploy applies all the migrations in sequence. No flag or staged rollout — the change is internally consistent at every step.

## Open Questions

1. **Channel-management UI route**: standalone page (`/projects/<slug>/settings/channels`) or a tab inside the existing project-edit page? Existing project-edit is a single-form page; cleaner to give Channels its own page. Default: standalone page.
2. **Article admin demote affordance**: admin form field on Article, or a separate "Demote" action button? Probably both — field for read state, button for action. To be decided at implementation.
3. **Image upload endpoint reuse**: the existing project-image upload endpoint is scoped to project edit. Reuse as-is, or scope a new article-image endpoint? Reuse, since the storage and security model are identical.
4. **Notification email template authoring**: do we want a single generic "you have an update" template that branches on discussion vs article, or two templates? Two templates is clearer and matches how the existing codebase splits transactional emails. Default: two templates.
