## 0. Architectural constraints (read first)

This codebase keeps API routers thin: **views/routers in `api/routers/` MUST NOT import from `apps.<x>.models` directly**, and MUST NOT call ORM methods (`.objects.filter(…)`, `.save()`, etc.) themselves. All data access goes through the service layer:

- `services/<domain>/query_interface.py` — abstract query interface (`ABC` + dataclasses for return values).
- `services/<domain>/handler_interface.py` — abstract mutation interface.
- `services/<domain>/django_impl/query.py` — Django ORM implementation of the query interface.
- `services/<domain>/django_impl/handler.py` — Django ORM implementation of the handler interface.
- `services/<domain>/exceptions.py` — domain exceptions.

For this change, that means a new `services/follows/` module with `query_interface.py`, `handler_interface.py`, `exceptions.py`, and `django_impl/`. The new `api/routers/follows.py` endpoints SHALL depend only on those interfaces and `request.user`; they SHALL NOT touch `Follow.objects` / `Channel.objects` / `FollowChannelPreference.objects` directly. Signal handlers MAY touch the models directly (they live inside the app boundary). Data migrations MAY touch the models directly via the migration's frozen-app model accessors. Mirror this convention for every backend task below.

## 1. Backend: `is_house_project` flag on Project

- [x] 1.1 Add `is_house_project: BooleanField(default=False)` to `Project` in `apps/projects/models.py`.
- [x] 1.2 Override `Project.save()` to raise `ValidationError` if `is_house_project=True` is being set when another row already has `is_house_project=True`. The guard SHALL allow re-saving the same house-project row (idempotent).
- [x] 1.3 Generate the schema migration (`uv run python manage.py makemigrations projects`) and edit it to add a Postgres partial unique constraint: `UniqueConstraint(fields=["is_house_project"], condition=Q(is_house_project=True), name="project_house_singleton")`.
- [x] 1.4 Tests in `apps/projects/`: saving a second `is_house_project=True` row raises; saving the same row a second time with the flag still True is a no-op; clearing the flag and setting it on a different row succeeds.

## 2. Backend: new `follows` app and `Channel` model

- [x] 2.1 Create `apps/follows/` (with `__init__.py`, `apps.py`, `models.py`, `admin.py`, `migrations/__init__.py`). Register it in `INSTALLED_APPS`.
- [x] 2.2 Add `Channel` model in `apps/follows/models.py`: `id (UUIDField pk)`, `project (FK to projects.Project, on_delete=CASCADE, related_name="channels")`, `name (CharField max_length=100)`, `created_at`, `updated_at`. `Meta.unique_together = (("project", "name"),)`. `Meta.db_table = "channels"`. `__str__` returns `f"{project.title}: {name}"`.
- [x] 2.3 Generate the initial migration for `follows` (`uv run python manage.py makemigrations follows`).
- [x] 2.4 Add a `post_save` signal handler on `Project` (in `apps/projects/signals.py`, registered in the projects app's `AppConfig.ready()`) that, when `created=True`, creates a `Channel(project=instance, name="Updates")`.
- [x] 2.5 Add `ChannelAdmin` with `list_display = ("name", "project", "created_at")` and `list_filter = ("project",)`.
- [x] 2.6 Tests: creating a new `Project` results in exactly one `Channel` named "Updates" linked to it. Bulk-creating projects skips the signal (documented; helper called explicitly by bulk callers).

## 3. Backend: `Follow` and `FollowChannelPreference` models

- [x] 3.1 Add `Follow` model in `apps/follows/models.py`: `id (UUIDField pk)`, `user (FK to AUTH_USER_MODEL, on_delete=CASCADE, related_name="follows")`, `project (FK to projects.Project, on_delete=CASCADE, related_name="followers")`, `created_at`. `Meta.unique_together = (("user", "project"),)`. `Meta.db_table = "follows"`.
- [x] 3.2 Add `FollowChannelPreference` model in `apps/follows/models.py`: `id (UUIDField pk)`, `follow (FK to Follow, on_delete=CASCADE, related_name="preferences")`, `channel (FK to Channel, on_delete=CASCADE)`, `email_enabled (BooleanField default=True)`, `in_app_enabled (BooleanField default=True)`. `Meta.unique_together = (("follow", "channel"),)`. `Meta.db_table = "follow_channel_preferences"`.
- [x] 3.3 Generate the schema migration for these two models.
- [x] 3.4 Add `FollowAdmin` and `FollowChannelPreferenceAdmin` with sensible `list_display` / `list_filter`.

## 4. Backend: auto-follow signal on User create

- [x] 4.1 Add helper `create_house_project_follow(user)` in `apps/follows/services.py`: looks up `Project.objects.filter(is_house_project=True).first()`. If found, creates a `Follow` for the user (via `get_or_create`) and a `FollowChannelPreference` for every Channel of that project (all-on). If no house project exists (greenfield dev DB), logs a warning and no-ops.
- [x] 4.2 Add a `post_save` signal on User in `apps/users/signals.py` (new file) that calls `create_house_project_follow(instance)` when `created=True` and `not instance.is_system_user`.
- [x] 4.3 Register the signal in `apps/users/apps.py` `AppConfig.ready()`.
- [x] 4.4 Tests in `apps/follows/tests/`: creating a new regular user creates a Follow + 3 per-channel prefs (all `email_enabled=True`, `in_app_enabled=True`) for the house project; creating a system user creates no Follow; creating a user when no house project exists logs a warning and creates no Follow (does not raise).

## 5. Backend: one-shot data migration

- [x] 5.1 Write `apps/follows/migrations/0002_seed_channels_and_house_follows.py` (sequence number depends on what's already there). The migration SHALL depend on the projects-app migration that added `is_house_project`.
- [x] 5.2 In `RunPython`: identify Naglasúpan by slug (literal value to be looked up at write time; if not found, log and return). Set `is_house_project=True` on that row.
- [x] 5.3 Get-or-create the three channels for the Naglasúpan row: "Updates" (signal will already create on new Projects, but be defensive), "Competition Winners", "Product Updates".
- [x] 5.4 For every other existing `Project`, get-or-create the "Updates" channel.
- [x] 5.5 For every `User` with `is_active=True` and `is_system_user=False`, in batches of 1000:
  - Create or get a `Follow(user=user, project=naglasupan)`.
  - Create or update three `FollowChannelPreference` rows (one per channel): "Competition Winners" email_enabled = `user.email_opt_in_competition_results`; "Product Updates" email_enabled = `user.email_opt_in_platform_updates`; "Updates" email_enabled = True. In-app for all three: True.
- [x] 5.6 Provide a reverse migration that deletes all `Follow`, `FollowChannelPreference`, and seeded `Channel` rows created by the forward migration. Setting `is_house_project=False` is also reversed.
- [ ] 5.7 Run the migration locally against a copy of prod data; verify counts and spot-check one opted-out user.

## 6. Backend: follow service layer

(Per the architectural constraint in §0: routers depend on these interfaces, not on models directly.)

- [x] 6.1 Create `services/follows/` with `query_interface.py`, `handler_interface.py`, `exceptions.py`, and `django_impl/` (with `query.py`, `handler.py`, and matching `test_query.py` / `test_handler.py`).
- [x] 6.2 Define `FollowQuery` ABC in `query_interface.py` with at least: `is_followed(user, project) -> bool`, `get_follow(user, project_slug) -> Follow | None`. Return dataclasses (e.g., `FollowState`) rather than ORM instances where the consumer is a router/schema.
- [x] 6.3 Define `FollowHandler` ABC in `handler_interface.py` with: `follow(user, project) -> FollowState` (idempotent — creates Follow + per-channel prefs if missing; returns existing state if already followed) and `unfollow(user, project) -> None` (idempotent hard-delete; cascade-deletes preferences).
- [x] 6.4 Define domain exceptions in `services/follows/exceptions.py` (e.g., `ProjectNotFoundError`). Reuse existing `services/project/exceptions.py` where it makes sense.
- [x] 6.5 Implement `DjangoFollowQuery` and `DjangoFollowHandler` in `services/follows/django_impl/`. These are the ONLY places that import the new models. The handler's `follow()` SHALL look up the project's Channels and create a `FollowChannelPreference` row per channel (all-on defaults).

## 7. Backend: follow router endpoints

- [x] 7.1 Add `api/routers/follows.py` with two endpoints, all thin handlers that delegate to the service layer:
  - `POST /api/projects/{slug}/follow` — auth required, idempotent. Resolves the project via the existing project query service; calls `FollowHandler.follow(...)`; returns the current state. 200 either way.
  - `DELETE /api/projects/{slug}/follow` — auth required, idempotent. Calls `FollowHandler.unfollow(...)`. Returns 204.
  - (No standalone GET — the project-detail response carries `is_followed`.)
- [x] 7.2 Add a Pydantic schema `FollowStateResponse` in `api/schemas/follow.py` exposing `is_followed: bool` and the follow's `created_at` (or `null`).
- [x] 7.3 Wire the router into the API root.
- [x] 7.4 Modify `api/schemas/project.py::ProjectResponse` to include a derived `is_followed: bool` field. The router/handler that builds `ProjectResponse` SHALL ask `FollowQuery.is_followed(request.user, project)` for the value (or `False` if anonymous) — NOT call `Follow.objects.filter(…)` directly.
- [x] 7.5 Regenerate the OpenAPI spec: `cd src/django-backend && make extract-openapi`.
- [x] 7.6 Tests in `services/follows/django_impl/test_*.py` cover the service layer; router-level tests cover the request/response contract (status codes, schema). Anonymous gets `is_followed=false` and 401 on POST/DELETE.

## 8. Backend: lint and tests pass

- [x] 8.1 Run `cd src/django-backend && make lint` and fix any issues.
- [x] 8.2 Run `cd src/django-backend && make test` and fix any failures.

## 9. Frontend: generated types and `FollowButton`

- [x] 9.1 `cd src/web-ui && npm run generate-types`.
- [x] 9.2 Add `src/web-ui/src/lib/api/follows.ts` exposing `follow(slug)` and `unfollow(slug)` methods that call the new endpoints.
- [x] 9.3 Add `src/web-ui/src/components/FollowButton.tsx`. Props: `projectSlug: string`, `initialIsFollowed: boolean`. State: `isFollowed`, `isPending`. Labels: "Follow" / "Following". Hidden if `useSession()` returns no user.
- [x] 9.4 On click: optimistic toggle, call the API, revert on error.
- [x] 9.5 Wire `FollowButton` into the project page header / top-bar location (matching the design's "subtle but visible" framing — implementation chooses the specific element).
- [x] 9.6 Style: matches existing top-bar button conventions (review existing similar buttons; pick the same Tailwind class set).

## 10. Frontend: lint and end-to-end

- [x] 10.1 `cd src/web-ui && npm run lint`.
- [ ] 10.2 Playwright check (Playwright MCP, using credentials from `.env.claude`): visit an approved project, see Follow button. Click → label becomes Following. Reload → still Following. Click → Follow. Log out → button hidden.

## 11. Manual prod-data sanity check (pre-merge)

- [ ] 11.1 Run the migration against a copy of prod data. Verify: (a) Naglasúpan has `is_house_project=True`; (b) the two named channels exist on Naglasúpan; (c) every other project has exactly one "Updates" channel; (d) every active non-system user has a Follow + 3 prefs on Naglasúpan; (e) a sample opted-out user has `email_enabled=False` on the matching channel.
- [ ] 11.2 Confirm the legacy broadcast email path still resolves the same recipient set as before (no regression — `services/email/django_impl/query.py::list_opted_in_for_broadcast_type` unchanged).
