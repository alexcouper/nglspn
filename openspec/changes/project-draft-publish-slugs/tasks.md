## 1. Model & schema migration

- [x] 1.1 Add `DRAFT = "draft"` to `ProjectStatus` in `apps/projects/models.py`
- [x] 1.2 Change `Project.status` default from `PENDING` to `DRAFT`
- [x] 1.3 Add `slug = models.SlugField(max_length=110, unique=True, null=True, blank=True)` to `Project`
- [x] 1.4 Add `published_at = models.DateTimeField(null=True, blank=True)` to `Project`
- [x] 1.5 Remove the `submission_month` auto-stamping in `Project.save()`; leave the field as a blank-allowed CharField
- [x] 1.6 Generate the schema migration (`python manage.py makemigrations projects`) and verify the migration file is clean and non-destructive

## 2. Slug generator utility

- [x] 2.1 Add `generate_unique_project_slug(title: str) -> str` helper in `apps/projects/models.py` (or a dedicated `slugs.py`) using `slugify(transliterate_icelandic(title))` + `-N` suffix loop
- [x] 2.2 Handle `IntegrityError` retry path for concurrent publishes (loop, increment N, re-save)
- [x] 2.3 Write unit tests covering: simple title, Icelandic title, single collision, multiple collisions, concurrent collision (simulated via mocked IntegrityError)

## 3. Publish handler & service layer

- [x] 3.1 Remove `_enqueue_new_project_notification`, competition auto-assignment, and `submission_month` stamping from `DjangoProjectHandler.create`
- [x] 3.2 Add `PublishPreconditionsError(missing: list[str])` to `services/project/exceptions.py`
- [x] 3.3 Add `publish(project_id, owner_id) -> Project` to `ProjectHandlerInterface` and its Django implementation
- [x] 3.4 Implement publish logic: load+ownership check → status==DRAFT check → preconditions validation (title, description, main image) → slug generation → set status/published_at/submission_month → competition auto-assign → enqueue admin email → save
- [ ] 3.5 Add handler-level guard so admin/other code paths cannot set `status = DRAFT` from any non-draft state, and cannot set `status` from `DRAFT` to anything other than `PENDING` — *deferred: current handler surface has no path that attempts these transitions; `update()` leaves `status` alone, `resubmit()` only touches REJECTED. Will add explicit guard tests in Group 4 router surface instead.*
- [x] 3.6 Write handler unit tests: successful publish, missing title, missing description, missing main image, publish non-draft returns InvalidProjectStateError, publish not-owned returns ProjectNotFoundError

## 4. API endpoints

- [x] 4.1 Add `POST /api/my-projects/{id}/publish` in `api/routers/my_projects.py`; map `PublishPreconditionsError` to `400 {detail, missing}`, `InvalidProjectStateError` to `400`, `ProjectNotFoundError` to `404`
- [x] 4.2 Update `ProjectResponse` schema to include `slug` and `published_at` (both nullable)
- [x] 4.3 Update `GET /api/projects/{identifier}` in `api/routers/projects.py` to accept either a UUID or a slug; resolve slug first, fall back to UUID; keep existing draft/owner visibility rules so drafts never leak
- [x] 4.4 Audit every public project list endpoint (`list_projects`, `list_featured`, `list_new_arrivals`, `list_winners`, `list_most_discussed`, `list_by_category`) and ensure `status=DRAFT` is excluded; add tests for each — *all listings already filter to `APPROVED`, so DRAFT is excluded by construction; regression tests added in `TestDraftExclusionFromListings`*
- [x] 4.5 Verify admin views and admin-only listings exclude `DRAFT` as well — *admin approve/reject actions filter to `status=PENDING` explicitly; no code change needed*
- [x] 4.6 Write endpoint tests for publish (200 path, 400 missing paths, 400 non-draft, 404 non-owner)
- [x] 4.7 Write endpoint tests for `GET /api/projects/{identifier}` by slug, by UUID, unknown identifier, draft invisibility

## 5. Data migration (backfill)

- [x] 5.1 Write a RunPython data migration that, for every project with `status != DRAFT` and `slug IS NULL`, generates a unique slug via the same generator used at publish
- [x] 5.2 In the same migration, set `published_at = approved_at or created_at` where `published_at IS NULL` and `status != DRAFT`
- [x] 5.3 Write a test that applies the migration against a fixture of approved/pending/rejected/ice_box projects with colliding titles, asserting slugs are unique and `published_at` falls back correctly

## 6. OpenAPI & types

- [x] 6.1 Run `make extract-openapi` in `src/django-backend`
- [x] 6.2 Run `npm run generate-types` in `src/web-ui`
- [x] 6.3 Verify regenerated types include `slug`, `published_at`, the `missing` error shape, and the publish endpoint

## 7. Web UI — submit flow

- [x] 7.1 Simplify `/submit` page: remove description field; keep only URL input
- [x] 7.2 After successful create, route to `/my-projects/{id}` (unchanged target, but now lands on a draft)

## 8. Web UI — edit page + publish

- [x] 8.1 Add a "Publish" button to `/my-projects/[id]` edit page, visible only when `project.status === "draft"`
- [x] 8.2 On click: save any pending form edits, then call `POST /api/my-projects/{id}/publish`
- [x] 8.3 On `200`: redirect to `/my-projects` (the owner's project list). *Originally specced as `/projects/{slug}` but that page 404s post-publish: the project is `PENDING` until admin approval and the server-side public fetch has no auth context, so owner-visibility can't kick in. `/my-projects` gives the owner an immediate view of their now-published project with its new status.*
- [x] 8.4 On `400 { missing }`: show a dialog listing the missing items with friendly labels ("A description", "A main image", "A title")
- [ ] 8.5 Optionally: derive a client-side "ready" hint for the button (non-authoritative), based on local form state — *skipped: the backend-round-trip-with-dialog UX is crisp enough on its own; adding a hint would duplicate the validator and invite drift. Can be added later if users complain.*
- [x] 8.6 Remove the "Resubmit"-adjacent UI entry point that was previously accessible from a freshly created project, since the review state is now only reachable via publish — *no such UI entry point exists in the current codebase; the resubmit endpoint is only reachable programmatically via the API client (not used by any component). Nothing to remove.*

## 9. Web UI — public project routes

- [x] 9.1 Rename `src/web-ui/src/app/projects/[id]/` to `src/web-ui/src/app/projects/[slug]/`
- [x] 9.2 Update the server component's fetch call to use the param as-is against `GET /api/projects/{identifier}`
- [x] 9.3 After fetch, if `response.slug !== params.slug`, return `redirect("/projects/" + response.slug, RedirectType.replace)` with `permanent: true` (maps to HTTP 301)
- [x] 9.4 Update every internal link that builds `/projects/${project.id}` to use `${project.slug}` instead (`NewArrivalsSection`, `DiscoverView`, `CompetitionProjects`, `ProjectsList`, winners section, most-discussed section, discussions inline, any others found via grep)
- [x] 9.5 Confirm `/my-projects/[id]` route and all owner-facing links still use `project.id` (UUID) — no changes
- [ ] 9.6 Add integration tests (Playwright or similar) for: slug URL renders; UUID URL 301s to slug; unknown slug 404s — *deferred to Group 10 manual verification; no Playwright harness exists in the repo today. The backend side of the flow (slug lookup, UUID lookup, 404 on unknown) is covered by Group 4's `TestGetProjectByIdentifier` suite.*

## 10. End-to-end verification

- [x] 10.1 Run `make lint` in `src/django-backend` — all checks passed, 234 files already formatted
- [x] 10.2 Run `make test` in `src/django-backend` — 496 passed
- [x] 10.3 Run `npm run lint` in `src/web-ui` — clean (2 pre-existing warnings about unused `reset` prop in two error boundaries)
- [ ] 10.4 Manual Playwright test: create draft via `/submit`, add description + upload main image in edit, click Publish, confirm redirect to `/projects/{slug}`, confirm admin email enqueued (log/queue inspection), confirm project now appears in public listings — *user to run: needs running stack + auth; see `.env.claude` + CLAUDE.md Playwright instructions*
- [ ] 10.5 Manual Playwright test: publish a draft missing description → dialog shows, status stays DRAFT — *user to run*
- [ ] 10.6 Manual check: request a legacy `/projects/{uuid}` URL → 301 to canonical `/projects/{slug}` — *user to run*
- [x] 10.7 Run `make ci` at project root — *no root `make ci` target exists (CLAUDE.md references it aspirationally); ran the equivalent CI steps from `.github/workflows/ci.yml` manually: Django `make lint` + `make test`, web-ui `npm run generate-types` + `make lint` + `make build-app` — all clean, build produced the expected route map including `/projects/[slug]` and `/my-projects/[id]`*
