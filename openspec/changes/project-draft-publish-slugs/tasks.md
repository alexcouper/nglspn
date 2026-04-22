## 1. Model & schema migration

- [x] 1.1 Add `DRAFT = "draft"` to `ProjectStatus` in `apps/projects/models.py`
- [x] 1.2 Change `Project.status` default from `PENDING` to `DRAFT`
- [x] 1.3 Add `slug = models.SlugField(max_length=110, unique=True, null=True, blank=True)` to `Project`
- [x] 1.4 Add `published_at = models.DateTimeField(null=True, blank=True)` to `Project`
- [x] 1.5 Remove the `submission_month` auto-stamping in `Project.save()`; leave the field as a blank-allowed CharField
- [x] 1.6 Generate the schema migration (`python manage.py makemigrations projects`) and verify the migration file is clean and non-destructive

## 2. Slug generator utility

- [ ] 2.1 Add `generate_unique_project_slug(title: str) -> str` helper in `apps/projects/models.py` (or a dedicated `slugs.py`) using `slugify(transliterate_icelandic(title))` + `-N` suffix loop
- [ ] 2.2 Handle `IntegrityError` retry path for concurrent publishes (loop, increment N, re-save)
- [ ] 2.3 Write unit tests covering: simple title, Icelandic title, single collision, multiple collisions, concurrent collision (simulated via mocked IntegrityError)

## 3. Publish handler & service layer

- [ ] 3.1 Remove `_enqueue_new_project_notification`, competition auto-assignment, and `submission_month` stamping from `DjangoProjectHandler.create`
- [ ] 3.2 Add `PublishPreconditionsError(missing: list[str])` to `services/project/exceptions.py`
- [ ] 3.3 Add `publish(project_id, owner_id) -> Project` to `ProjectHandlerInterface` and its Django implementation
- [ ] 3.4 Implement publish logic: load+ownership check → status==DRAFT check → preconditions validation (title, description, main image) → slug generation → set status/published_at/submission_month → competition auto-assign → enqueue admin email → save
- [ ] 3.5 Add handler-level guard so admin/other code paths cannot set `status = DRAFT` from any non-draft state, and cannot set `status` from `DRAFT` to anything other than `PENDING`
- [ ] 3.6 Write handler unit tests: successful publish, missing title, missing description, missing main image, publish non-draft returns InvalidProjectStateError, publish not-owned returns ProjectNotFoundError

## 4. API endpoints

- [ ] 4.1 Add `POST /api/my-projects/{id}/publish` in `api/routers/my_projects.py`; map `PublishPreconditionsError` to `400 {detail, missing}`, `InvalidProjectStateError` to `400`, `ProjectNotFoundError` to `404`
- [ ] 4.2 Update `ProjectResponse` schema to include `slug` and `published_at` (both nullable)
- [ ] 4.3 Update `GET /api/projects/{identifier}` in `api/routers/projects.py` to accept either a UUID or a slug; resolve slug first, fall back to UUID; keep existing draft/owner visibility rules so drafts never leak
- [ ] 4.4 Audit every public project list endpoint (`list_projects`, `list_featured`, `list_new_arrivals`, `list_winners`, `list_most_discussed`, `list_by_category`) and ensure `status=DRAFT` is excluded; add tests for each
- [ ] 4.5 Verify admin views and admin-only listings exclude `DRAFT` as well
- [ ] 4.6 Write endpoint tests for publish (200 path, 400 missing paths, 400 non-draft, 404 non-owner)
- [ ] 4.7 Write endpoint tests for `GET /api/projects/{identifier}` by slug, by UUID, unknown identifier, draft invisibility

## 5. Data migration (backfill)

- [ ] 5.1 Write a RunPython data migration that, for every project with `status != DRAFT` and `slug IS NULL`, generates a unique slug via the same generator used at publish
- [ ] 5.2 In the same migration, set `published_at = approved_at or created_at` where `published_at IS NULL` and `status != DRAFT`
- [ ] 5.3 Write a test that applies the migration against a fixture of approved/pending/rejected/ice_box projects with colliding titles, asserting slugs are unique and `published_at` falls back correctly

## 6. OpenAPI & types

- [ ] 6.1 Run `make extract-openapi` in `src/django-backend`
- [ ] 6.2 Run `npm run generate-types` in `src/web-ui`
- [ ] 6.3 Verify regenerated types include `slug`, `published_at`, the `missing` error shape, and the publish endpoint

## 7. Web UI — submit flow

- [ ] 7.1 Simplify `/submit` page: remove description field; keep only URL input
- [ ] 7.2 After successful create, route to `/my-projects/{id}` (unchanged target, but now lands on a draft)

## 8. Web UI — edit page + publish

- [ ] 8.1 Add a "Publish" button to `/my-projects/[id]` edit page, visible only when `project.status === "draft"`
- [ ] 8.2 On click: save any pending form edits, then call `POST /api/my-projects/{id}/publish`
- [ ] 8.3 On `200`: redirect to `/projects/{response.slug}`
- [ ] 8.4 On `400 { missing }`: show a dialog listing the missing items with friendly labels ("A description", "A main image", "A title")
- [ ] 8.5 Optionally: derive a client-side "ready" hint for the button (non-authoritative), based on local form state
- [ ] 8.6 Remove the "Resubmit"-adjacent UI entry point that was previously accessible from a freshly created project, since the review state is now only reachable via publish

## 9. Web UI — public project routes

- [ ] 9.1 Rename `src/web-ui/src/app/projects/[id]/` to `src/web-ui/src/app/projects/[slug]/`
- [ ] 9.2 Update the server component's fetch call to use the param as-is against `GET /api/projects/{identifier}`
- [ ] 9.3 After fetch, if `response.slug !== params.slug`, return `redirect("/projects/" + response.slug, RedirectType.replace)` with `permanent: true` (maps to HTTP 301)
- [ ] 9.4 Update every internal link that builds `/projects/${project.id}` to use `${project.slug}` instead (`NewArrivalsSection`, `DiscoverView`, `CompetitionProjects`, `ProjectsList`, winners section, most-discussed section, discussions inline, any others found via grep)
- [ ] 9.5 Confirm `/my-projects/[id]` route and all owner-facing links still use `project.id` (UUID) — no changes
- [ ] 9.6 Add integration tests (Playwright or similar) for: slug URL renders; UUID URL 301s to slug; unknown slug 404s

## 10. End-to-end verification

- [ ] 10.1 Run `make lint` in `src/django-backend`
- [ ] 10.2 Run `make test` in `src/django-backend`
- [ ] 10.3 Run `npm run lint` in `src/web-ui`
- [ ] 10.4 Manual Playwright test: create draft via `/submit`, add description + upload main image in edit, click Publish, confirm redirect to `/projects/{slug}`, confirm admin email enqueued (log/queue inspection), confirm project now appears in public listings
- [ ] 10.5 Manual Playwright test: publish a draft missing description → dialog shows, status stays DRAFT
- [ ] 10.6 Manual check: request a legacy `/projects/{uuid}` URL → 301 to canonical `/projects/{slug}`
- [ ] 10.7 Run `make ci` at project root
