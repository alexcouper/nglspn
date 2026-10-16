# Tasks: author-owned articles

Backend paths are under `src/django-backend/`, web-ui paths under
`src/web-ui/src/`. Each group ends green on `make lint` and `make test` for
the side it touches; groups 1–3 are commits on their own.

## 0. Prerequisite

- [x] 0.1 Archive `openspec/changes/user-profile-page` (`openspec archive
  user-profile-page`) so `openspec/specs/user-profile-page/spec.md` exists;
  verify `openspec validate author-owned-articles --strict` still passes.

## 1. Rename `ProjectImage` → `Image`

- [ ] 1.1 Rename the model in `apps/projects/models.py`, set
  `db_table = "images"`, rename `ProjectImageQuerySet`, and generate a
  migration containing only `RenameModel` and `AlterModelTable`; verify
  `uv run python manage.py makemigrations --check --dry-run` is clean.
- [ ] 1.2 Rename every other backend occurrence (services, routers, admin
  classes, signals, management commands, `scripts/seed_db.py`,
  `scripts/seed_prod_copy.py`, `tests/factories.py`) and
  `ProjectImageResponse` → `ImageResponse` in `api/schemas/project.py`; verify
  `make lint` and `make test` pass and `grep -rn ProjectImage --include=*.py`
  returns only migrations.
- [ ] 1.3 `make extract-openapi`, commit `src/web-ui/backend-openapi.json`,
  `npm run generate-types`, rename the `ProjectImage` alias in
  `lib/api/articles.ts` and `lib/api/my-projects.ts` to `Image` and update its
  importers; verify web-ui `make lint` and `make test` pass.

## 2. Models and migrations

- [ ] 2.1 `apps/projects/models.py`: `Image.project` nullable, add the
  "project or article" `CheckConstraint`, make `__str__` null-safe; migration;
  model test that a row with neither owner is rejected.
- [ ] 2.2 `apps/follows/models.py`: `Channel.owner` (FK User, CASCADE,
  nullable, `related_name="personal_channels"`), `Follow.followed_user` (FK
  User, CASCADE, nullable, `related_name="followed_by"`); replace both
  `unique_together` with `UniqueConstraint`s per target; add the exactly-one
  checks and the `user != followed_user` check; `PERSONAL_CHANNEL_NAME`
  constant; null-safe `__str__`s; migration; model tests for each rejected
  shape per `specs/user-following/spec.md`.
- [ ] 2.3 `apps/articles/models.py`: `project` and `channel` nullable;
  narrow `articles_project_slug_uniq` to `project IS NOT NULL`; add
  `articles_author_slug_uniq` on `(author, slug)` where `project IS NULL`; add
  the project-implies-channel check; null-safe `__str__`; migration; model
  tests for the two slug constraints and the check.
- [ ] 2.4 `apps/users/signals.py`: `pre_delete` receiver on `User` deleting
  the user's author-owned articles; test that deleting a user with one
  author-owned and one project article leaves only the project one, with
  `author` null.
- [ ] 2.5 `apps/follows/signals.py`: the channel `post_save` receiver enrols
  `Follow.objects.filter(followed_user=instance.owner)` when `owner` is set;
  test that a follower of a person gains a `FollowedChannel` row when the
  person's channel is created.
- [ ] 2.6 Admin: `apps/articles/admin.py`, `apps/follows/admin.py`,
  `apps/projects/admin.py` columns, search and `render_link` tolerate a null
  project and show the author/owner; `apps/notifications/admin.py` digest
  preview counter keys on project title or author name; verify the admin
  changelists load with an author-owned article, a personal channel and a
  user follow seeded (`make seed` gains one of each).

## 3. Services: articles, images, follows, notifications, feed, users

- [ ] 3.1 `apps/articles/slugs.py`: scope `assign_unique_article_slug` and
  the existence check by project, or by `(author, project IS NULL)`; tests for
  the three slug scenarios in `specs/author-articles/spec.md`.
- [ ] 3.2 `services/articles`: `create_draft` accepts `project_id=None` with
  no channel; `update_article` rejects `channel_id` on an author-owned article
  (`ChannelOnWrongProjectError` or a new `NoChannelForAuthorArticleError` →
  422); `publish` on an author-owned article `get_or_create`s the personal
  channel and sets `article.channel` before the state change; listing-image
  validation accepts the article's own image or the project match; tests
  cover first and second publish, the channel attach, and the listing-image
  rejection.
- [ ] 3.3 `services/storage.py`: `generate_article_upload_key(article_id,
  filename)` → `articles/{article_id}/{unique}/{filename}`;
  `services/images/django_impl/handler.py`: `_reserve` takes
  `project | None` and picks the key by owner, `complete_upload` and
  `delete_image` tolerate a null project, `create_article_upload` passes
  `article.project`; `services/images/django_impl/query.py` unchanged;
  tests: upload against an author-owned article lands under `articles/`, has
  variants, is reaped and tombstoned like a project one.
- [ ] 3.4 `services/follows`: `follow_user` / `unfollow_user` on the handler
  (idempotent, self-follow raises, enrols the personal channel if present);
  `is_following_user` on the query; `FollowWithPreferences` gains `target`,
  `user_id`, `user_name`, `user_avatar_url`, project fields optional;
  `list_follows_with_preferences` selects `followed_user` and its avatar and
  channels; tests per `specs/user-following/spec.md` endpoints requirement
  and the mixed `GET /api/follows` scenario.
- [ ] 3.5 `services/notifications/django_impl/handler.py`: drop the
  `follow__project_id` filter, make the house check
  `channel.project_id is not None and channel.project.is_house_project`,
  `_build_article_group` emits `project=None` plus a new `NotificationAuthor`
  (id, name, avatar URL) on `NotificationGroup`; tests: author-owned fan-out
  reaches the person's followers, no house log line, project follower is not
  delivered a person's article.
- [ ] 3.6 `services/email/django_impl/article_digest.py` and the five
  `templates/email/_article_*` / `article_digest_*` templates: `_article_url`
  by container, byline from the author when there is no project, no icon;
  `send_article_digest_sample` still runs; snapshot/content tests for an
  author-owned entry in each template.
- [ ] 3.7 `apps/feed/models.py`: `visible_subject` admits
  `article__project__isnull=True`; `services/users/django_impl/query.py`:
  `list_public_articles_for` admits author-owned articles and
  `list_own_articles_for` returns everything the user authored with state;
  tests: author-owned entry renders and leaves on demotion; public list mixes
  both kinds; own list includes drafts and pending.

## 4. API and OpenAPI

- [ ] 4.1 New `api/routers/article_items.py` mounted at `/api/articles`:
  `GET`, `PATCH`, `DELETE /{id}`, `POST /{id}/publish`, the three image
  routes, with `can_edit(article, user)` in `api/routers/_helpers.py`; remove
  the id-addressed routes from `api/routers/articles.py`; move the tests in
  `test_articles.py` and `test_article_images.py` across and add the
  stranger-404, author-patch and `channel_id`-422 cases.
- [ ] 4.2 `api/routers/auth.py`: `POST /me/articles` (create author-owned
  draft) and `GET /me/articles`; `api/routers/users.py`:
  `GET /{id}/articles/by-slug/{slug}`, `POST` / `DELETE /{id}/follow`,
  `is_followed` on the profile response via a `UserProfileResponse` subclass;
  tests per the endpoint requirements in `specs/author-articles/spec.md` and
  `specs/user-following/spec.md`, including 404 for system/inactive users and
  400 for self-follow.
- [ ] 4.3 Schemas: `ArticleOut.project` and `UserArticleResponse.project`
  optional; `FeedArticleRef.project_title` optional plus `author_id`,
  `author_name`, `author_avatar_url`; `NotificationGroupResponse.project`
  optional plus `author`; `FollowResponse` gains `target`, `user_id`,
  `user_name`, `user_avatar_url`, project fields optional; `OwnArticleResponse`
  with `state` and `global_visibility`; verify `make extra-tests` passes after
  `make extract-openapi` and the file is committed.

## 5. Web UI: editor and routes

- [ ] 5.1 `git mv` the non-route files from `app/projects/[slug]/articles/`
  (components, hooks, tests) to `app/articles/`, and the shared render pieces
  (`ArticleRenderContent`, `ArticleOnward`, `onward.ts`, `origin.ts` and
  tests) with them; fix imports; verify `make lint` and `make test` pass with
  no behaviour change.
- [ ] 5.2 `lib/api/articles.ts`, `lib/uploadImage.ts`, `lib/api/users.ts`,
  `lib/api/auth.ts`: id-addressed calls drop the project ref; add
  `createOwn`, `listOwn`, `getBySlugForUser`; `npm run generate-types` picks
  up the new schemas; unit tests for the URL builders.
- [ ] 5.3 `app/articles/edit/[articleId]/page.tsx` + `ArticleAuthoringRoute`
  loading the article first, then the project if any; `ArticleAuthoringPage`
  hides `ChannelDropdown` and points the breadcrumb at the profile for an
  author-owned article; `useArticleDraft` navigates back to the container
  after publish/delete; `app/projects/[slug]/articles/edit/[articleId]/page.tsx`
  becomes a `redirect()`; `article-authoring-route.test.tsx` covers both
  containers and the redirect.
- [ ] 5.4 `Container` union in `app/articles/container.ts`; thread it through
  `ArticleRenderContent`, `ArticleOnward`, `onward.ts`, `origin.ts`; new
  `app/users/[id]/articles/[articleSlug]/page.tsx` building the author
  container with metadata naming the author; tests for the author header,
  "More from {name}", Follow button target and the 404 shapes.
- [ ] 5.5 `app/users/[id]/page.tsx`: Follow button (not on own profile,
  login redirect when anonymous), "Write article" on own profile calling
  `createOwn` and routing to the editor, owner's list from `listOwn` with
  `articleBadge` / `sortDraftsFirst` moved into `lib/article-listing.ts`,
  public list rows for author-owned articles showing the author and linking
  to the user URL; `ArticleCard` accepts an author flag in place of
  `projectTitle`; tests for own vs visitor views and the badges.
- [ ] 5.6 `components/FollowButton.tsx`, `FollowPopover.tsx`,
  `hooks/useChannelToggle.ts`, `lib/api/follows.ts`,
  `app/profile/following/page.tsx`: a `target` prop (`project` slug or `user`
  id); the Following page renders user entries with avatar, name, profile link
  and the channel toggle; tests for both targets.
- [ ] 5.7 `app/latest/feedEntry.ts` + `FeedRow.tsx`: flag and href from the
  author when `project_title` is null; `lib/notifications.ts` +
  `components/NotificationGroupItem.tsx`: head and deep-link by author when
  `project` is null; tests for the author-owned row and group.
- [ ] 5.8 UI strings: new keys in `i18n/articles/en.json`,
  `i18n/profile/en.json`, `i18n/notifications/en.json` for the author-flavoured
  copy (follow/unfollow a person, "More from {name}", "Write article" on the
  profile, badges if they move); no new entry in `eslint-rules/i18n-pending.mjs`;
  `make lint` passes.

## 6. Integration

- [ ] 6.1 Backend `make lint && make extra-tests && make test`; web-ui
  `make lint && make test && make build-app && make extra-tests` (the moved
  editor must stay inside its route bundle budget).
- [ ] 6.2 Playwright spec `e2e/author-article.spec.ts`: U writes and publishes
  an article from their profile; V follows U from the profile, sees the
  article in Latest flagged with U's name, opens it at
  `/users/{U.id}/articles/{slug}`, and finds it in the bell; run against a
  seeded local stack per `CLAUDE.md` (mind the 5/min login limit).
- [ ] 6.3 `docs/2026-08-19-article-launch-followups.md`: mark the "no signal
  why an article never appeared" item as closed for author-owned articles by
  the profile badge; `CLAUDE.md` file-locations table gains
  `app/articles/` for the editor; verify both read correctly.
