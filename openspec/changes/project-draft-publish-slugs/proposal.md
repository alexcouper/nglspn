## Why

Today, submitting a project immediately puts it into review: the admin is notified before the project is really ready, and the owner is pushed through a two-step creation dialog (URL + description) before they've had a chance to shape the page. Separately, projects are addressed by UUID, which blocks us from introducing human-readable URLs. Since a project's title can change over time, any slug scheme needs a clear "snapshot" moment where the slug is frozen — otherwise we'd have to track historical slugs indefinitely.

This change introduces a draft-and-publish lifecycle. Owners build their project in private, and the act of publishing is the single moment when the project becomes reviewable, is tied to a competition and submission month, and receives its permanent slug. Slugs are generated once at publish and never change again.

## What Changes

- Add a new `DRAFT` status to projects, preceding the existing `PENDING` state.
- New projects are created in `DRAFT` with only a website URL — no description is collected at creation.
- Move submission-month assignment, competition auto-assignment, and the admin notification email from project creation to project publication.
- Add a new `POST /my-projects/{id}/publish` endpoint that validates publish preconditions (title, description, main image) and returns `400 { missing: [...] }` when unmet.
- Add an `/my-projects/{id}/publish` action in the web UI; clicking it triggers save-then-publish, surfacing missing items in a dialog when the project is not ready.
- Add `slug` (unique, nullable-until-published) and `published_at` (datetime, nullable) fields to the `Project` model.
- Generate project slugs from `title` at publish time using the existing `transliterate_icelandic` + `slugify` helpers; resolve collisions by appending `-2`, `-3`, etc. Slugs never change after publish, even if the title is edited.
- **BREAKING (URLs)**: Public project URLs move from `/projects/[uuid]` to `/projects/[slug]`. UUID URLs 301-redirect to the canonical slug URL via middleware.
- Public `GET /projects/{identifier}` endpoint accepts either a slug or a UUID, resolving to the same project. The response always includes the canonical `slug`, which the frontend middleware uses to decide whether to issue a 301 redirect. No separate lookup endpoint.
- Owner-facing `/my-projects/[id]` continues to use UUID (unchanged).
- Draft projects can only be deleted or published — they cannot be approved, rejected, or iced. Once published, a project cannot be unpublished (delete only).
- Data migration: backfill `slug` for all existing non-draft projects using the collision-safe generator, and set `published_at = approved_at or created_at`.

## Capabilities

### New Capabilities
- `project-draft-publish`: Draft status on projects, the publish endpoint and its preconditions, one-way DRAFT → PENDING transition, and the publish-time side effects (submission month, competition assignment, admin notification, `published_at`).
- `project-slugs`: Generation of unique, immutable project slugs at publish time, slug-based public URL routing, and 301 redirects from legacy UUID URLs.

### Modified Capabilities
- None. No existing specs describe project creation or project URL routing at the requirement level.

## Impact

- **Django backend (`apps/projects`)**: Add `DRAFT` to `ProjectStatus`, add `slug` and `published_at` fields + migration, add a backfill migration for existing projects. Move side effects (email, competition assignment, `submission_month`) out of the create handler and into a new publish handler. New endpoint in `api/routers/my_projects.py`. Public-facing project queries that list projects must exclude `DRAFT`.
- **Services (`services/project`)**: Add a `publish` method to `ProjectHandlerInterface` and its Django implementation, including the preconditions validator and slug generator. Update `create` to stop assigning competition/submission_month/notification.
- **Web UI (`src/web-ui`)**: Simplify `/submit` to URL-only; add a "Publish" button and missing-requirements dialog to `/my-projects/[id]`. Move public project route from `/projects/[id]` to `/projects/[slug]`; the page fetches via `GET /projects/{identifier}` and, if the URL param differs from the canonical slug in the response, middleware issues a 301 to the slug URL. Update all internal links to use slugs.
- **OpenAPI**: Regenerate spec and TS types after endpoint changes.
- **Emails / notifications**: No change to content — only the moment they fire shifts from create to publish.
- **Existing data**: One-time backfill migration for slugs and `published_at` on all non-draft projects. No DRAFT projects exist historically, so no status backfill needed.
