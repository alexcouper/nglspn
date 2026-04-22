## Context

Project creation today is a single step: the owner submits URL + description, the project is created in `PENDING`, an admin email fires, the project is auto-assigned to the currently-open competition, and its `submission_month` is stamped with "now". The owner is then dropped on a rich edit page to add images, tagline, long description, and tags — but the review signal has already been sent.

Separately, public projects are addressed by UUID (`/projects/[id]`). Because project titles can change freely, we have never committed to a slug: doing so would require tracking historical slugs or accepting breakage on rename.

This change decouples "create" from "make reviewable" by inserting a `DRAFT` state, and uses the single publish transition as the anchor point for a permanent, immutable slug. All side effects that currently fire at creation time — admin email, competition assignment, submission month — move to publish, alongside new slug generation and a new `published_at` timestamp.

Key existing pieces:
- `Project.status` is a `TextChoices` field with `PENDING / APPROVED / REJECTED / ICE_BOX`. Default is `PENDING`.
- `ProjectHandlerInterface.create` handles creation, competition assignment, and admin email.
- `transliterate_icelandic` and `slugify` already exist and are used by `Competition.save()`.
- Next.js public page lives at `/projects/[id]`; the owner edit page at `/my-projects/[id]`.

## Goals / Non-Goals

**Goals:**
- One-way lifecycle: `DRAFT → PENDING → (APPROVED | REJECTED → PENDING via resubmit | ICE_BOX)`. Drafts cannot be rejected, approved, or iced.
- Draft projects produce no admin email and no competition assignment until published.
- Slugs are generated at publish, unique across all projects, and immutable thereafter — even when the title is later edited.
- Public URLs become human-readable (`/projects/[slug]`); old UUID URLs continue to work via 301 redirects.
- Backend enforces publish preconditions; frontend reflects missing items back to the user without needing a separate requirements endpoint.

**Non-Goals:**
- Changing the review/approval workflow itself (handled by the separate `moderator-project-approval` change).
- Supporting slug edits or historical slug tracking.
- Backfilling draft status for any existing projects — they are all already published in effect.
- Unpublishing. Once published, the only escape is delete.
- Changing the owner-facing `/my-projects/[id]` route or its underlying API (stays on UUID).

## Decisions

### 1. `DRAFT` is a new `ProjectStatus` value, not a separate field

**Decision:** Add `DRAFT = "draft"` as a new choice on the existing `ProjectStatus` enum. Change the model default from `PENDING` to `DRAFT`.

**Why:** A separate `is_draft` boolean would create two sources of truth for "what state is this project in" and require every status filter to also check `is_draft`. Treating draft as just another status keeps the state machine linear and queries simple (`status=draft` excludes everything public-facing by construction, since all existing list endpoints filter by `status=approved` or similar).

**Alternative considered:** Separate `is_draft: bool` + keep `status` defaulting to `pending`. Rejected because it duplicates the concept of lifecycle state.

**Implication:** Every place that queries projects must be audited. Anywhere that doesn't explicitly filter to `APPROVED` (e.g., any listing that shows `PENDING` projects to admins) must now also exclude `DRAFT`.

### 2. Allowed transitions

```
DRAFT ──publish──► PENDING ──approve──► APPROVED
  │                   │
  │ delete            ├──reject──► REJECTED ──resubmit──► PENDING
  ▼                   └──icebox──► ICE_BOX
 gone
```

- `DRAFT → PENDING`: only via `POST /my-projects/{id}/publish`.
- `DRAFT → {APPROVED, REJECTED, ICE_BOX}`: forbidden. Enforced at the handler/admin level.
- `PENDING/APPROVED/REJECTED/ICE_BOX → DRAFT`: forbidden. No unpublishing.
- Delete is allowed from any state (unchanged behavior).

### 3. Publish preconditions: backend-authoritative, no separate requirements endpoint

**Decision:** `POST /my-projects/{id}/publish` validates required fields (title, description, at least one image marked `is_main=True` with `upload_status=UPLOADED`) and returns `400 { detail: "...", missing: [ "title" | "description" | "main_image" ] }` when any are absent. Success is `200 ProjectResponse`.

**Why:** A separate `GET .../publish-requirements` endpoint would need to stay in sync with the publish validator, inviting drift. One endpoint is the single source of truth.

**Frontend UX:** The Publish button is always clickable when the project is in `DRAFT`. Click flow:
1. Save any pending edits.
2. POST to publish.
3. On `200`, navigate to `/projects/{slug}`.
4. On `400` with `missing`, surface a dialog that lists the missing items.

A lightweight client-side check can grey out the button or show a hint count, but the backend is authoritative.

### 4. Slug generation: `slugify(transliterate_icelandic(title))` with `-N` collision suffix

**Decision:** At publish:
```
base = slugify(transliterate_icelandic(title))
if Project.objects.filter(slug=base).exists():
    n = 2
    while Project.objects.filter(slug=f"{base}-{n}").exists():
        n += 1
    slug = f"{base}-{n}"
else:
    slug = base
```
A unique constraint on the column guarantees correctness; the loop above just picks the next available `-N` in the happy path. Under concurrent publishes we rely on the DB unique constraint to raise `IntegrityError`, which we catch and retry with the next `-N`.

**Why:** `-N` suffixes keep URLs human. Random suffixes are ugly and offer nothing here — we're not trying to hide project IDs.

**Alternative considered:** Short random hash suffix (e.g. `my-project-a3f2`). Rejected because it's uglier without meaningful benefit; the projects are public, ordering is not sensitive.

### 5. Slug is frozen at publish

**Decision:** After publish, editing the title does not regenerate the slug. The `slug` field is writable only by the publish handler; update paths leave it alone.

**Why:** This is the whole motivation for the draft/publish gate. Mutable slugs reintroduce the tracking burden we're trying to avoid.

**Trade-off:** An owner who fat-fingers their title at publish lives with that slug forever. Acceptable because (a) they can preview/edit the title freely in draft, and (b) the project can be deleted and re-created if truly needed.

### 6. Public endpoint accepts either UUID or slug; response carries canonical `slug`

**Decision:** `GET /api/projects/{identifier}` resolves the path param as either a UUID or a slug. The response shape includes `slug` as a non-nullable field for published projects (nullable for drafts, but drafts never reach this endpoint).

**Flow for the Next.js public page:**
1. Page handler receives `params.slug` (whatever's in the URL).
2. Fetches `GET /api/projects/{params.slug}`.
3. Compares `response.slug` to `params.slug`. If different (i.e. the URL was a UUID, or an old slug), returns `redirect(307 → /projects/{response.slug}, permanent: true)` — Next.js turns this into a 301 on the wire.
4. Otherwise, renders.

**Why:** One endpoint, one round-trip, no separate lookup endpoint. UUID-shape detection is simple (`try UUID(param)`), and the router tries slug lookup first so the slug path is the fast path.

**Alternative considered:**
- Slug-only endpoint + separate `GET /projects/lookup/{uuid}`. Rejected: two endpoints to maintain.
- Middleware that sniffs the URL shape and prefetches. Rejected: extra request for no benefit.

### 7. Side-effect migration: create → publish

Currently, `Project.save()` stamps `submission_month` if unset, and `ProjectHandler.create` handles competition auto-assignment + admin notification. Post-change:

- `Project.save()`: **remove** the `submission_month` default. The column stays non-null (no data migration needed, since existing rows already have it), but the model no longer auto-populates it at create time.
- Actually, since new rows would violate NOT NULL when created without `submission_month`, we must either (a) allow blank at the DB level, or (b) stamp a placeholder like `""` at create and overwrite at publish. **Chosen: make `submission_month` blank-allowed** (it's already `CharField(max_length=7)`, which permits empty string by default in Django; no DB-level change needed). The publish handler writes the real value.
- `ProjectHandler.create`: stop assigning competition. Stop calling `_enqueue_new_project_notification`. Still validates tags, stores URL.
- New `ProjectHandler.publish(project_id, owner_id)`:
  - Loads project, verifies owner.
  - Verifies `status == DRAFT`; else `InvalidProjectStateError`.
  - Verifies preconditions (title, description, main image); else returns missing list.
  - Generates unique slug from title.
  - Sets `status = PENDING`, `published_at = now()`, `submission_month = now().strftime("%Y-%m")`.
  - Auto-assigns to the currently open competition, if any.
  - Calls `_enqueue_new_project_notification`.
  - Saves + returns project.

### 8. Data migration

A single migration that, for every project where `status != DRAFT` and `slug IS NULL`:
- Compute `slug` using the same generator as the publish handler. Uniqueness is enforced as rows are written.
- Set `published_at = approved_at or created_at`. We pick the most meaningful timestamp available; `approved_at` is the closest analogue for already-approved projects, but not all projects will have it (e.g., legacy PENDING), so we fall back to `created_at`.

No existing projects are in `DRAFT`, so no status changes are needed. The migration runs in data-migration form (RunPython) after the schema migration that adds the columns.

### 9. Frontend routing

- Next.js public route moves from `/projects/[id]/page.tsx` to `/projects/[slug]/page.tsx`. The directory rename is just cosmetic; the server component inside does the fetch + canonical redirect described in Decision 6.
- Owner route `/my-projects/[id]` stays exactly as is.
- Internal links (winners, discover sections, most-discussed, etc.) that today build `/projects/${project.id}` links are updated to use `project.slug` when present. Where the API response type currently exposes only `id`, extend it to include `slug`.

## Risks / Trade-offs

- **Risk: Existing `/projects/[uuid]` links in emails, external bookmarks, third-party blog posts break if the redirect path has any bug.** → The page handler always performs the UUID-or-slug lookup and 301s to slug. Covered by tests. Emails sent going forward should use slug URLs.
- **Risk: Someone publishes with a slug they dislike, and can't change it.** → Documented trade-off. Users can edit freely in draft; they see the generated slug after publish in the URL of the success redirect. A future "delete and recreate" escape hatch exists.
- **Risk: Concurrent publishes with the same base slug race on `-N` selection.** → DB unique constraint catches it. Handler retries on `IntegrityError` by incrementing N. In practice, publish is low-volume.
- **Risk: Public listing endpoints silently include drafts after the model change.** → Audit every project query during implementation; explicitly exclude `DRAFT` in list endpoints. Tests must cover that a `DRAFT` project does not appear in any public listing.
- **Risk: `submission_month` ending up blank in bad paths** (e.g., a publish that fails partway, a direct admin-shell create). → Acceptable; admins can fix via admin UI. Draft projects genuinely don't have a submission month until publish.
- **Trade-off: Adding `DRAFT` to the enum forces an audit of every status-based query.** Necessary cost of making drafts first-class; cheaper than a parallel boolean that would quietly go wrong.
- **Trade-off: `GET /api/projects/{identifier}` accepting two param types blurs the contract slightly.** Mitigated by clear docstring + tests for both paths, and by response always carrying canonical `slug`.

## Migration Plan

1. Ship the schema migration (add `slug`, `published_at`, extend `status` choices). No data change yet. Safe to deploy alone.
2. Ship the data migration (backfill `slug` and `published_at` for non-draft projects).
3. Ship the handler + endpoint changes (publish endpoint, create simplification, side-effect move).
4. Ship the web UI changes (submit form simplification, publish button + dialog, route rename, middleware 301).
5. Regenerate OpenAPI spec + TS types at each relevant step.

Rollback: each step is independently reversible until step 3 is deployed (after which some projects may be in `DRAFT` status). If rollback is needed post-step-3, a one-off migration can promote any `DRAFT` projects to `PENDING` manually.

## Open Questions

- Should published project URLs include the Icelandic characters when the title is Icelandic? Current decision: no — the existing `transliterate_icelandic` helper already strips them, and that's consistent with how `Competition.slug` works today. Flagging in case the product preference differs.
- Does the admin detail page need to surface `DRAFT` projects anywhere? Default answer: no, but confirm during implementation that admin queryset filters exclude them.
