# Tasks: user profile page

Design reference: https://claude.ai/artifact/EtycAMJgbaSXFN7vuFHALR

## 1. Backend: avatar model and lifecycle

- [x] 1.1 Add `UserAvatar` to `apps/users/models.py` (fields per
  `specs/user-avatar/spec.md`) and a nullable `User.avatar` FK with
  `on_delete=SET_NULL`; run `makemigrations users` and commit the migration.
- [x] 1.2 Add a `pre_delete` receiver for `UserAvatar` that writes an
  `OrphanedStorageObject` tombstone, mirroring the `ProjectImage` receiver.
- [x] 1.3 Add `generate_avatar_upload_key(user_id, filename)` to
  `services/storage.py` producing `avatars/{user_id}/{unique}/{filename}`, with
  the same filename sanitising as `generate_upload_key`.
- [x] 1.4 Add `MAX_AVATAR_FILE_SIZE = 2 MB` and `AVATAR_CONTENT_TYPES`
  (jpeg, png, webp) next to the existing image limits in
  `services/images/handler_interface.py`.
- [x] 1.5 Extend `UserHandlerInterface` and `DjangoUserHandler` with
  `create_avatar_upload(user, meta) -> PreparedUpload`,
  `complete_avatar_upload(user, avatar, *, width, height) -> User` and
  `remove_avatar(user) -> User`. Completion verifies the object exists via the
  storage service, marks the row uploaded, repoints `User.avatar`, and deletes
  the previous row.
- [x] 1.6 In `services/images/django_impl/handler.py::_reap_abandoned_uploads`,
  add a second batch over stale `pending` `UserAvatar` rows using the shared
  `PENDING_UPLOAD_MAX_AGE_HOURS`.
- [x] 1.7 Tests in `services/users/django_impl/test_handler.py`: reservation
  writes a pending row and leaves `User.avatar` alone; completion repoints and
  deletes the old row; completion with a missing object raises; removal nulls
  and deletes. Tests in `services/images/django_impl/test_orphaned_objects.py`:
  replaced avatar drained, abandoned avatar reaped, fresh one left alone.

## 2. Backend: schemas and endpoints

- [x] 2.1 `api/schemas/user.py`: add `avatar_url: str | None` and
  `created_at: datetime` to `PublicUserProfile`; add `avatar_url` to
  `UserResponse`; a shared resolver reads `obj.avatar` and returns the URL only
  when the row is uploaded.
- [x] 2.2 Add `UserProjectResponse` (`id`, `slug`, `title`, `tagline`,
  `category_name`, `main_image_thumb_url`, `role`) and `UserArticleResponse`
  (`ArticleListItem` public fields plus `project: {slug, title}`) to
  `api/schemas/user.py`.
- [x] 2.3 Extend `UserQueryInterface` / `DjangoUserQuery` with
  `list_public_projects_for(user_id)` (approved projects via
  `ProjectContributor`, owners first then `published_at` desc, thumb URL via the
  discover-list helpers in `services/project/django_impl/query.py`) and
  `list_public_articles_for(user_id)` (`globally_visible_q()` and project
  approved, `published_at` desc, `select_related` project and channel).
- [x] 2.4 `api/routers/users.py`: switch `get_public_profile` to
  `REPO.users.get_active_by_id` plus an `is_system_user` check; add
  `GET /{user_id}/projects` and `GET /{user_id}/articles` sharing that 404
  rule.
- [x] 2.5 `api/routers/auth.py`: add `POST /me/avatar/upload-url`,
  `POST /me/avatar/{image_id}/complete` and `DELETE /me/avatar`, mapping
  `ImageError` subclasses to 400 as the article image endpoints do.
- [x] 2.6 Tests in `api/routers/test_users.py`: 404 for inactive and system
  users; projects list roles, order and status filtering; articles list
  visibility and project-status filtering; private fields still absent. Tests in
  `api/routers/test_avatar.py` for the three avatar endpoints, including the
  cross-user 404 and the 400 cases.
- [x] 2.7 `make lint`, `make test`, then `make extract-openapi` and commit
  `src/web-ui/backend-openapi.json`; `make extra-tests` must pass.

## 3. Web UI: API client and shared components

- [x] 3.1 `npm run generate-types`; extend `src/lib/api/users.ts` with
  `listProjects(userId)` and `listArticles(userId)`, and `src/lib/api/auth.ts`
  with `getAvatarUploadUrl`, `completeAvatarUpload` and `removeAvatar`.
- [x] 3.2 Add `src/components/Avatar.tsx`: `src`, `firstName`, `lastName`,
  `size`; renders the image or initials per the spec, with the display name as
  the accessible label. Unit test the initials rules.
- [x] 3.3 Add an optional `roleLabel` prop to `ProjectTile.tsx` rendered as a
  small chip beside the category line; leave existing callers unchanged.
- [x] 3.4 Add `src/lib/avatarBlob.ts`: given an image element and a `CropRect`,
  draw the region to a 512×512 canvas and return a JPEG `Blob`. Unit test the
  geometry with a stubbed canvas.

## 4. Web UI: public profile page

- [x] 4.1 Rebuild `src/app/users/[id]/page.tsx` to the design: header (avatar,
  name, "Joined <month year> · N projects · N articles", "Edit profile" when
  `user.id === id`), About card, Projects grid of `ProjectTile`s with role
  labels, Articles list of `ArticleCard`s (`grid` variant) prefixed with the
  project name and linking to `/projects/{slug}/articles/{articleSlug}`. Three
  parallel fetches, per-section skeletons, one-line empty states, "User not
  found" on 404 with no list requests.
- [x] 4.2 Extract the About renderer into `src/components/ProfileAbout.tsx`
  using `react-markdown` with `disallowedElements={["img"]}`, shared with the
  edit page's Preview.
- [x] 4.3 Delete `src/app/profile/ReadOnlyProfile.tsx`.
- [x] 4.4 Tests: `src/app/users/[id]/profile-page.test.tsx` covering full
  profile, empty sections, 404, and Edit-profile visibility for own vs other
  profile; a test that image markdown is dropped.

## 5. Web UI: edit page and settings split

- [x] 5.1 Move `Settings.tsx` to `src/app/profile/settings/page.tsx` behind
  `useRequireAuth`, keeping its behaviour; add a "Settings" entry to
  `UserMenu.tsx`.
- [x] 5.2 Rewrite `src/app/profile/page.tsx` as the edit page: avatar block
  (Upload photo → file input → `ImageCropper` with `lockRatio: 1` → blob →
  reserve → `uploadImage` → complete; Remove → delete), name fields, About with
  Write/Preview tabs using `ProfileAbout`, helper text, link card to
  `/profile/settings`. Save = one `PUT /api/auth/me` then `router.push` to
  `/users/{me}`; Cancel = `router.push` without saving; keep the both-names-empty
  guard.
- [x] 5.3 Remove the Edit/Preview `viewMode` toggle and its imports.
- [x] 5.4 Tests: `src/app/profile/edit-page.test.tsx` for save payload and
  navigation, cancel, both-names guard, preview rendering, avatar remove call,
  and the not-an-image error path.

## 6. Verify

- [ ] 6.1 `make lint`, `make test`, `make build-app`, `make extra-tests` in
  `src/web-ui/`; add a `/users/[id]` line to `bundle-budgets.json` if the
  default budget would hide a regression on this route.
- [x] 6.2 `uv run python manage.py makemigrations --check --dry-run` in
  `src/django-backend/` reports nothing.
- [ ] 6.3 Manual pass against `make dev` in both services with the seeded
  database (mind the 5/min login limit): open a byline link → profile renders
  with projects and articles; own profile shows Edit profile; upload, replace
  and remove an avatar, confirming the nav button follows; save About and see it
  on the public page; `/profile/settings` still saves cadence; a system user's
  id 404s; phone width has no horizontal scroll.
- [ ] 6.4 Playwright: add `src/web-ui/e2e/profile.spec.ts` covering the public
  page render and the edit → save → public round trip. Keep it out of CI as the
  rest of `e2e/` is.
