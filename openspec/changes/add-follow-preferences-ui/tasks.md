## 0. Architectural constraints (read first)

This codebase keeps API routers thin: **views/routers in `api/routers/` MUST NOT import from `apps.<x>.models` directly**, and MUST NOT call ORM methods (`.objects.filter(…)`, `.save()`, etc.) themselves. All data access goes through the service layer:

- `services/<domain>/query_interface.py` — abstract query interface (`ABC` + dataclasses for return values).
- `services/<domain>/handler_interface.py` — abstract mutation interface.
- `services/<domain>/django_impl/query.py` — Django ORM implementation of the query interface.
- `services/<domain>/django_impl/handler.py` — Django ORM implementation of the handler interface.
- `services/<domain>/exceptions.py` — domain exceptions.

For this change, that means extending the `services/follows/` module created in Phase 1 (`add-project-following`) with new query methods (list a user's follows, read one project's preferences) and new handler methods (update a single preference, including the mirror-write side-effect). The new endpoints in `api/routers/follows.py` SHALL depend only on those interfaces and `request.user`; they SHALL NOT touch `Follow.objects` / `FollowChannelPreference.objects` / `User.objects` directly. The mirror-write helper that touches `User.email_opt_in_*` lives **inside the handler implementation** (`services/follows/django_impl/handler.py`), not in the router. Mirror this convention for every backend task below.

## 1. Backend: schemas

- [ ] 1.1 Add `FollowChannelPreferenceResponse` schema: `channel_id`, `channel_name`, `email_enabled`, `in_app_enabled`.
- [ ] 1.2 Add `FollowResponse` schema: `project_slug`, `project_title`, `project_hero_image_url` (nullable), `created_at`, `channels: list[FollowChannelPreferenceResponse]`.
- [ ] 1.3 Add `FollowChannelPreferencePatch` schema: `email_enabled: bool | None`, `in_app_enabled: bool | None` (at least one required at request time — enforced in the handler, not the schema).
- [ ] 1.4 Add a list response wrapper for `GET /api/follows` (a `FollowsListResponse` or just `list[FollowResponse]` depending on existing patterns).

## 2. Backend: service-layer extensions

(Per §0: routers SHALL NOT touch ORM models. All new query/mutation logic lives in `services/follows/`, extending the module created in Phase 1. Routers in section 3 are thin pass-throughs.)

- [ ] 2.1 Extend `services/follows/query_interface.py` with:
  - `list_user_follows(user) -> list[FollowWithPreferences]` — returns one dataclass per follow with the project's slug/title/hero-image-url, `created_at`, and a list of per-channel preference dataclasses (channel id, channel name, `email_enabled`, `in_app_enabled`).
  - `get_follow_preferences(user, project_slug) -> FollowWithPreferences | None` — returns `None` when the user has no follow for the project.
- [ ] 2.2 Implement these methods in `services/follows/django_impl/query.py` using `select_related("project")` + `prefetch_related("preferences__channel")` to keep query count bounded.
- [ ] 2.3 Extend `services/follows/handler_interface.py` with:
  - `set_channel_preference(user, project_slug, channel_id, email_enabled=None, in_app_enabled=None) -> ChannelPreferenceState` — updates one row. Raises domain exceptions for: project not found, channel not on this project, no follow for `(user, project)`, no preference row for `(follow, channel)`, neither field provided.
- [ ] 2.4 Implement `set_channel_preference` in `services/follows/django_impl/handler.py`. The implementation SHALL:
  - Validate the channel belongs to the project (raise `ChannelNotOnProjectError` otherwise).
  - Validate the follow exists (raise `NotFollowingError` otherwise).
  - Validate at least one field was provided (raise `EmptyPatchError` otherwise).
  - Apply the updates with `update_fields=[...]` on the preference row.
  - Call the private mirror helper described in 2.5 when `email_enabled` changed.
- [ ] 2.5 Add a private `_mirror_legacy_email_flag(user, channel, email_enabled)` inside `services/follows/django_impl/handler.py` (not exported). Behaviour: if `channel.project.is_house_project` is True AND `channel.name in ("Competition Winners", "Product Updates")`, update the matching `User.email_opt_in_*` field and save with `update_fields=[...]`. Other cases are no-ops. Use the constant `LEGACY_FLAG_BY_CHANNEL_NAME = {"Competition Winners": "email_opt_in_competition_results", "Product Updates": "email_opt_in_platform_updates"}`; "Updates" is intentionally absent.
- [ ] 2.6 **Modify** the Phase 1 `unfollow(user, project)` handler implementation (in `services/follows/django_impl/handler.py`) to, when the deleted Follow is on the house project, additionally set both `email_opt_in_*` flags on the user to `False`. The mirror logic stays inside the handler. (The Phase 1 router code does not change — it still calls `FollowHandler.unfollow(...)`.)
- [ ] 2.7 Add domain exceptions in `services/follows/exceptions.py`: `NotFollowingError`, `ChannelNotOnProjectError`, `EmptyPatchError`.
- [ ] 2.8 Tests in `services/follows/django_impl/test_query.py`: `list_user_follows` returns correct shape for users with 0, 1, many follows; `get_follow_preferences` returns the right channels and None when not following.
- [ ] 2.9 Tests in `services/follows/django_impl/test_handler.py`:
  - `set_channel_preference` updates the row and returns the new state.
  - Mirror fires for Naglasúpan "Competition Winners" → `email_opt_in_competition_results`.
  - Mirror fires for Naglasúpan "Product Updates" → `email_opt_in_platform_updates`.
  - Mirror does NOT fire for Naglasúpan "Updates".
  - Mirror does NOT fire for non-house-project channels.
  - Mirror does NOT fire when only `in_app_enabled` was patched.
  - `unfollow` on house project sets both legacy flags to False.
  - `unfollow` on non-house project leaves legacy flags untouched.
  - Domain exceptions raised in each error case.

## 3. Backend: router endpoints

(Routers SHALL be thin: validate request, call the service, map service result/exceptions to HTTP responses. No `.objects` calls in this file.)

- [ ] 3.1 Add `GET /api/follows` in `api/routers/follows.py`. Authentication required. Calls `FollowQuery.list_user_follows(request.user)`; maps to `list[FollowResponse]`.
- [ ] 3.2 Add `GET /api/projects/{slug}/follow/preferences` in `api/routers/follows.py`. Authentication required. Calls `FollowQuery.get_follow_preferences(request.user, slug)`; 404 if `None`, 200 with `FollowResponse` otherwise.
- [ ] 3.3 Add `PATCH /api/projects/{slug}/follow/channels/{channel_id}`. Authentication required. Calls `FollowHandler.set_channel_preference(...)`. Maps `NotFollowingError` / `ChannelNotOnProjectError` / project-not-found → 404; `EmptyPatchError` → 400; success → 200 with `FollowChannelPreferenceResponse`.
- [ ] 3.4 Router-level tests: status codes for each path (200 / 400 / 404 / 401). The service-layer mirror-write behaviour is covered by §2.9 tests; the router tests only assert request → response wiring.

## 4. Backend: OpenAPI and tests

- [ ] 4.1 Regenerate the OpenAPI spec: `cd src/django-backend && make extract-openapi`.
- [ ] 4.2 Run `make lint` and `make test`. Fix any failures.

## 5. Frontend: generated types and API client

- [ ] 5.1 `cd src/web-ui && npm run generate-types`.
- [ ] 5.2 Extend `src/web-ui/src/lib/api/follows.ts` with `listFollows()`, `getFollowPreferences(slug)`, `patchFollowChannel(slug, channelId, body)`.

## 6. Frontend: FollowPopover component

- [ ] 6.1 Add `src/web-ui/src/components/FollowPopover.tsx`. Props: `projectSlug`, `onUnfollow` callback. On open, calls `getFollowPreferences(slug)`. Renders a list of `{channel_name}` rows with two `<Toggle>` controls (email, in-app).
- [ ] 6.2 Each toggle uses optimistic update: flip local state, call `patchFollowChannel`, revert + toast on error.
- [ ] 6.3 At the bottom, an "Unfollow" link calls `unfollow(slug)` from the existing Phase 1 client, then closes the popover and calls `onUnfollow()`.
- [ ] 6.4 Style consistent with existing popover/menu patterns in the codebase.
- [ ] 6.5 Tests: rendering shows the channels; toggle flips state and calls the API; failed PATCH reverts state and toasts; Unfollow calls the API and fires the callback.

## 7. Frontend: FollowButton open-popover behaviour

- [ ] 7.1 Modify `src/web-ui/src/components/FollowButton.tsx` (from Phase 1): when `isFollowed === true`, click opens `FollowPopover` instead of calling unfollow. When `isFollowed === false`, click still instantly follows.
- [ ] 7.2 Pass an `onUnfollow` callback that sets `isFollowed = false` and closes the popover.
- [ ] 7.3 Tests: in unfollowed state click → follow API + state flip; in followed state click → popover opens; Unfollow inside popover → state flips and popover closes.

## 8. Frontend: Followed projects page

- [ ] 8.1 Add the route at `src/web-ui/src/app/profile/followed-projects/page.tsx` (or the equivalent path under existing user settings). Auth-gated.
- [ ] 8.2 Server-fetches `listFollows()` and renders.
- [ ] 8.3 Each row: project icon/title, "N channels" chip, expand/collapse affordance, "Unfollow" link.
- [ ] 8.4 Expanded state: the same channel × medium toggles as the popover. Optimistic updates via `patchFollowChannel`.
- [ ] 8.5 "Unfollow" link removes the row from the list immediately and calls the API.
- [ ] 8.6 Empty state: short message + link back to Discover.
- [ ] 8.7 Add a "Followed projects" link to the user-settings sidebar / nav.
- [ ] 8.8 Tests: page renders for a user with multiple follows; expanding a row shows toggles; toggle updates the row + persists; Unfollow removes the row.

## 9. Frontend: lint and end-to-end

- [ ] 9.1 `cd src/web-ui && npm run lint`.
- [ ] 9.2 Playwright (using `.env.claude` credentials):
  - On a project page, click "Following" → popover opens, channels and toggles are visible.
  - Toggle an in-app switch → reload → switch state persists.
  - Click Unfollow inside popover → button reverts to "Follow".
  - Navigate to `/profile/followed-projects` → see Naglasúpan and any other followed projects, expand → see channel toggles, toggle one, reload, still persistent.
  - Toggle the Naglasúpan "Competition Winners" email switch off → verify (via API or DB inspection) that `email_opt_in_competition_results` on the user row is now False.

## 10. Cross-system invariant tests

- [ ] 10.1 Test (backend integration): user toggles Naglasúpan "Competition Winners" email off via PATCH. The legacy broadcast pipeline (`resolve_broadcast_recipients` for `email_type="competition_results"`) excludes them.
- [ ] 10.2 Test (backend integration): user toggles Naglasúpan "Product Updates" email off via PATCH. The legacy broadcast pipeline excludes them from `platform_updates`.
- [ ] 10.3 Test (backend integration): user unfollows Naglasúpan. The legacy broadcast pipeline excludes them from both types thereafter.
