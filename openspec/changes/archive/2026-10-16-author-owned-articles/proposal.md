# Proposal: author-owned articles

Issue: [#106](https://github.com/codalens/nglspn/issues/106), the first half of
[#105](https://github.com/codalens/nglspn/issues/105). The second half, RSS
feeds as outbound cards (#107), is not in this change but the image and channel
decisions below leave it a place to land.

## Why

An individual with something to say has to create a project to say it.
`Article.project` and `Article.channel` are required (`apps/articles/models.py:77-86`),
`Channel` hangs off `Project`, and `Follow` is `(user, project)`. A reader who
likes someone's writing can only follow one of that person's projects. The
profile page (#92) now shows what a person has done here, but the only way to
have written anything is through a project.

## What Changes

- **An article can belong to its author instead of a project.** `Article.project`
  and `Article.channel` become nullable: a project article keeps both, an
  author-owned one has no project and takes its author's personal channel on
  publish. Slug
  uniqueness for a project-less article is per author. It is read at
  `/users/{id}/articles/{slug}` and listed in Latest and on the author's
  profile.
- **A person can be followed.** A Follow button on the public profile. Following
  a person delivers their articles to the bell and the article digest on the
  same terms as following a project's channel: the person owns a `Channel`,
  created on their first publish, and the existing `FollowedChannel` fan-out
  runs unchanged. Following a person does **not** deliver their projects,
  comments or competition entries.
- **`Channel` and `Follow` each gain a user target**, exclusive with the project
  one: `Channel.project | Channel.owner`, `Follow.project | Follow.followed_user`.
  Exactly one is set. The auto-enrol signal that enrols a project's followers in
  a new channel does the same for a person's followers.
- **`ProjectImage` becomes `Image`** with a nullable `project`, so an article
  without a project can carry images. An `Image` belongs to a project or to an
  article; project articles keep both set as today. Images of a project-less
  article are stored under `articles/{article_id}/`.
- **The author's own article list gains a home outside my-projects.** The owner's
  profile lists every article they wrote, including drafts, with the same
  draft / pending review / not shown badges `MyProjectArticles` shows today, and
  a "Write article" entry point that creates the draft and opens the editor.
- **BREAKING (internal API): article routes addressed by id move out from under
  the project slug.** `PATCH`, `publish`, `DELETE`, and the three image routes
  become `/api/articles/{id}/…`; authorisation is derived from the article
  (project `full_edit`, or being the author of a project-less one). Creation
  and slug reads stay per container: `POST /api/projects/{slug}/articles` and
  `GET …/articles/by-slug/{slug}` as today, plus `POST /api/auth/me/articles`
  and `GET /api/users/{id}/articles/by-slug/{slug}`. The editor route follows:
  `/articles/edit/{id}` replaces `/projects/{slug}/articles/edit/{id}`.
- **BREAKING (internal API): `GET /api/follows` entries carry a target.**
  `project_*` fields become nullable and a `user` block is added; the Following
  page renders both kinds.
- **Response shapes that assumed a project become nullable:** `ArticleOut.project`,
  `UserArticleResponse.project`, `FeedArticleRef.project_title`,
  `NotificationGroupResponse.project`. Each gains the author alongside, and the
  feed flag, the notification group header, the digest email byline and the
  article page header show the author's name where they showed the project.
- **Feed visibility** for an article becomes "no project, or project approved"
  and the article's own visibility gate, which already keys on author trust
  (`_resolve_visibility_on_publish`), carries over unchanged.
- `PublicUserProfile` gains `is_followed`. Additive.

Out of scope: a username or handle in URLs (the id stays), channel management
for a person (one channel, named for them, not editable), RSS (#107), and any
feed event other than an article publish.

## Capabilities

### New Capabilities

- `author-articles`: an article owned by its author — the model rule, slug
  scope, where its images live, the public URL and render page, the owner's
  article list and entry point, and the id-addressed article routes.
- `user-following`: following a person — the `Follow` and `Channel` user
  targets, the follow endpoints on `/api/users/{id}`, the personal channel's
  creation and enrolment, and how it appears in `GET /api/follows`.

### Modified Capabilities

- `articles`: the model requirement (nullable `project` / `channel`, `Image`
  instead of `ProjectImage`), slug uniqueness scope, the authoring endpoint and
  entry point (editor route), and the render page (a second URL shape).
- `project-following`: `Follow` carries `project` or `followed_user`; the
  `GET /api/follows` response shape.
- `notifications`: the house-channel check tolerates a channel without a
  project; `NotificationGroup.project` is optional and an author is carried.
- `latest-feed`: entry state for an article without a project (flag is the
  author), and the visibility rule for its entry.

`user-profile-page` (`openspec/changes/user-profile-page/`, merged in #92 but
not archived) is touched by this change — its "articles are listed with their
project" requirement loosens, and the profile page gains a Follow button and
the owner's list. Archive it first so the main spec exists to delta against;
until then the new behaviour is specified in `author-articles` and
`user-following`.

## Impact

**Backend** (`src/django-backend/`)

- Models and migrations: `apps/articles` (nullable FKs, check constraint, second
  slug constraint), `apps/follows` (`Channel.owner`, `Follow.followed_user`,
  constraints, unique rules), `apps/projects` (`ProjectImage` → `Image`,
  nullable `project`, check constraint, table rename). All in the same change.
- `ProjectImage` is named in 25 non-test files (108 occurrences) plus
  `tests/factories.py`; the rename is mechanical but wide. Frontend type alias
  `ProjectImage` in `lib/api/articles.ts` and `lib/api/my-projects.ts` follows.
- `services/articles`: `create_draft` for an author, slug scoping, channel and
  listing-image validation that today compares `project_id`s
  (`handler.py:402,443-464`), `delete_channel`'s last-channel guard.
- `services/follows`: handler and query interfaces are project-keyed
  throughout; they gain user-keyed twins. `apps/follows/signals.py:39` enrols
  by owner as well as by project.
- `services/notifications/django_impl/handler.py:122-131,220,227`: group
  building and the house check. `services/email/django_impl/article_digest.py`
  and the five `templates/email/_article_*` / `article_digest_*` templates:
  byline and URL from the author when there is no project.
- `apps/feed/models.py:51` visibility; `services/users/django_impl/query.py:131`
  public article list; `services/images/django_impl/handler.py` reservation and
  storage key; admin for articles, channels, follows, images, notification
  digest preview.
- `api/routers/articles.py`, `channels.py`, `follows.py`, `users.py`; schemas
  `article.py`, `feed.py`, `notification.py`, `follow.py`, `user.py`.
- **OpenAPI**: `make extract-openapi` and commit `src/web-ui/backend-openapi.json`.

**Web UI** (`src/web-ui/`)

- Editor moves to `app/articles/edit/[articleId]/`; the components under
  `app/projects/[slug]/articles/` that are not route files move with it.
  `ArticleAuthoringRoute` stops loading a project before the article.
- New `app/users/[id]/articles/[articleSlug]/` render page sharing
  `ArticleRenderContent`, `ArticleOnward`, `onward.ts`, `origin.ts`, all of
  which take a project today.
- `app/users/[id]/page.tsx`: Follow button, owner's article list, Write article.
- `components/FollowButton.tsx`, `FollowPopover.tsx`, `hooks/useChannelToggle.ts`,
  `app/profile/following/page.tsx`, `lib/api/follows.ts`: a user target.
- `app/latest/feedEntry.ts`, `components/NotificationGroupItem.tsx`,
  `lib/notifications.ts`, `components/ArticleCard.tsx`: author in place of
  project. `lib/uploadImage.ts`, `lib/api/articles.ts`: new routes.
- UI strings in `src/i18n/articles/en.json`, `notifications/en.json`,
  `users/en.json` (or the profile area's file) for the author-flavoured copy.

**Storage.** New `articles/{article_id}/…` key prefix in the same bucket; the
bucket policy is prefix-agnostic. Existing article images stay under
`projects/`.

**Not touched:** the login rate limit, the 10-image project cap (project-less
articles have no gallery to cap), onboarding, competitions, discussions, the
sitemap (#96 remains separate; a project-less article is one more URL shape for
it to enumerate when it happens).
