# Design: author-owned articles

## Context

See [`proposal.md`](proposal.md) for motivation and the six spec deltas under
[`specs/`](specs/) for the behaviour. The mechanics that shape the decisions:

- Delivery is already channel-based. The fan-out selects recipients off
  `FollowedChannel` by `channel_id` (`services/notifications/django_impl/handler.py:218`)
  and never reads `Follow.project` except as a redundant filter on the same
  query. `Follow` is the row the button creates; `FollowedChannel` hangs off it;
  the auto-enrol receiver (`apps/follows/signals.py:39`) fills the gap between
  the two when a channel appears after the follow.
- Every uploaded image is a `ProjectImage` with a non-null `project`
  (`apps/projects/models.py:227`). Article images are the same rows with
  `article` set, excluded from galleries by that link, stored under
  `projects/{project_id}/`, with WebP variants and a `pre_delete` tombstone for
  the orphan drain. The listing-image check compares `project_id`s
  (`services/articles/django_impl/handler.py:454-464`).
- Trust is per author already: `_resolve_visibility_on_publish` reads
  `article.author.article_trust` (`handler.py:73-81`); nothing in the gate
  touches the project. `MyProjectArticles.tsx:47-63` already renders
  draft / published / pending review / not shown badges from `state` and
  `global_visibility`.
- Every article route is nested under `/api/projects/{slug}` and authorises by
  `require_full_edit(slug)` (`api/routers/articles.py:287-293`). The editor
  loads the project before the article (`ArticleAuthoringRoute.tsx:54`).
- The render page and its onward/origin helpers take a `Project`
  (`[articleSlug]/page.tsx:86-112`, `onward.ts`, `origin.ts`). The profile page
  (`app/users/[id]/page.tsx`) shows the public article list via
  `GET /api/users/{id}/articles`, which filters `project__status = APPROVED`.
- `user-profile-page`'s design chose a separate `UserAvatar` over a nullable
  `ProjectImage.project`, on the grounds that a fourth kind of row would
  complicate every gallery query. That reasoning is revisited below.

## Goals / Non-Goals

**Goals:**

- One rule, in two places: `Channel` and `Follow` each point at a project or a
  user, exactly one. `FollowedChannel`, the fan-out, the digest and the
  auto-enrol receiver do not learn a second path.
- An author-owned article is a normal `Article` for every reader of the model:
  same visibility gate, same slug mechanics, same image lifecycle, same feed
  event. Readers that print the project learn to print the author; nothing
  else changes.
- No new storage, queue or external dependency.

**Non-Goals:**

- A feed-event model for "what this person did". Following a person is
  following their personal channel, full stop.
- Channel management for a person. One channel, created for them, no UI.
- A username in URLs. `/users/{id}` is what the profile page shipped with.
- Moving existing article images out of `projects/{project_id}/`.
- Account deletion as a product feature. The `pre_delete` rule below exists so
  the schema stays consistent under admin and test deletes.

## Decisions

### Nullable `project` with an "exactly one owner" check, not a parallel model

`Article.project`, `Article.channel`, `Channel.project`, `Follow.project` and
`Image.project` all become nullable, each paired with a new nullable FK and a
`CheckConstraint`:

| Model | Pair | Constraint |
|---|---|---|
| `Channel` | `project` / `owner` | exactly one non-null |
| `Follow` | `project` / `followed_user` | exactly one non-null; `user != followed_user` |
| `Image` | `project` / `article` | at least one non-null |
| `Article` | `project` / `channel` | `project` null, or both non-null |

*Alternatives considered.* A hidden personal project per user: zero schema
change, but a lie in every project count, listing and sitemap forever.
Separate `UserChannel` / `UserFollow` / `ArticleImage` models: cleaner on
paper, but each one forks a code path that today has exactly one consumer —
the fan-out would read two tables, the Following page two lists, the variant
pipeline two models. The nullable pair keeps every consumer on one query with
one extra `OR`.

This is the opposite call from `user-profile-page`'s `UserAvatar`, and
deliberately so. An avatar has a different lifecycle from a gallery image: no
variants, no article link, no gallery exclusion, replace-in-place. An image of
an author-owned article has *exactly* the lifecycle of an existing article
image — the only thing that differs is which FK is null. Giving it its own
model would duplicate `_reserve`, `complete_upload`, variant generation and the
sweep for no behavioural gain.

### `ProjectImage` → `Image`, table included

The class name is wrong once a row can have no project. Rename the model, the
`db_table` (`project_images` → `images`, an `AlterModelTable`; nothing outside
migrations names the table), the Pydantic `ProjectImageResponse` → `ImageResponse`
(which renames the OpenAPI component and so the generated TS type), and the
frontend alias `ProjectImage` in `lib/api/articles.ts` and
`lib/api/my-projects.ts`. Related names stay: `Project.images`,
`Article.images`, `listing_for_articles`. 108 non-test occurrences across 25
backend files plus `tests/factories.py`; ruff and `tsc --noEmit` catch any
miss, so the rename is a mechanical first task on its own commit.

*Alternative:* keep the table name pinned, as `FollowedChannel` did. That
precedent was about a rename that bought nothing; this one is the whole point.

### The personal channel is created on first publish and attached to the article

`HANDLERS.articles.publish` on an author-owned article calls
`get_or_create(Channel, owner=author, name=PERSONAL_CHANNEL_NAME)` and sets
`article.channel` before the state change. The `post_save` receiver on
`Channel` then enrols every `Follow(followed_user=author)` synchronously,
exactly as it enrols a project's followers today, so by the time the fan-out
task runs the `FollowedChannel` rows exist. No backfill migration, no empty
channels for the majority who never write, and someone who follows a person
before they publish is in the tolerated "follow with no channels" state the
follows design already accepts.

Attaching the channel to the article — rather than leaving `channel` null and
teaching the fan-out to look up `author.channel` — is what keeps
`create_notifications_for_article`, `_build_article_group`, the digest and the
house-channel check reading `article.channel` unchanged. The fan-out drops its
`follow__project_id = article.project_id` filter: a `FollowedChannel` row only
ever points at a channel of its follow's target, so the filter was redundant
and would now exclude every person-follow.

`PERSONAL_CHANNEL_NAME` is a constant ("Articles"). It is unique per owner by
construction and is not shown on cards: `feedEntry.ts:71` already hides a
channel name equal to the flag; the author-owned branch hides it outright.

*Alternative:* create the channel at signup. Needs a data migration for every
existing user and leaves a channel on every account for a feature most will
never use.

### `Follow.followed_user` mirrors `Channel.owner`

`Follow` gets `followed_user` (FK User, CASCADE), `unique (user, followed_user)`
alongside the existing `(user, project)`, and a check that the two are not the
same user. `FollowHandlerInterface` gains `follow_user` / `unfollow_user`;
`follow_channel` / `unfollow_channel` are untouched because the Following page
toggles a channel by id under an existing follow and the new target reaches
them through `GET /api/follows`. The query layer's `FollowWithPreferences`
grows `target`, `user_id`, `user_name`, `user_avatar_url`, with the project
fields optional.

`is_followed` for a person is returned by `GET /api/users/{id}` only, on a
`UserProfileResponse(PublicUserProfile)` subclass resolved in the router.
`PublicUserProfile` itself is embedded in every project and article response
and the profile-page design requires it be answerable from the user row alone;
a per-requester field there would be a query per byline.

### Authorisation is derived from the article, and id routes move to `/api/articles`

A new router at `/api/articles/{id}` carries `GET`, `PATCH`, `DELETE`,
`publish` and the three image routes. Each resolves the article then calls
`can_edit(article, user)`: author of an author-owned article, or
`REPO.project.user_can_edit(article.project_id, user)` for a project one. A
miss is 404 — same as `require_full_edit` today — so the id leaks nothing.
`api/routers/articles.py` keeps the project-scoped `POST` and `GET` list and
`by-slug`; `api/routers/users.py` gains `GET /{id}/articles/by-slug/{slug}`;
`api/routers/auth.py` gains `POST /me/articles` and `GET /me/articles` beside
`/me/avatar`.

*Alternative:* keep the project-nested id routes and add a `/users/{id}/…`
twin set. Two routers doing the same thing with different slugs, and the
editor still has to know which to call. The web-ui is the only client, it
ships in the same pipeline, and the project-nested forms were only ever an
accident of where authorisation lived.

### One editor route, loading the article first

`app/articles/edit/[articleId]/` becomes the editor route; the components and
hooks under `app/projects/[slug]/articles/` that are not route files move to
`app/articles/` with it (`git mv`, tests included), and
`app/projects/[slug]/articles/edit/[articleId]/page.tsx` becomes a
`redirect()`. `ArticleAuthoringRoute` fetches `GET /api/articles/{id}` with the
caller's token, then `api.projects.get(article.project.slug)` only when there is
a project — the project is needed for the channel dropdown and the breadcrumb,
nothing else. `useArticleDraft`'s post-publish and post-delete navigation and
`uploadImage.ts`'s target take the article id instead of a project ref.

### A `Container` union for the render page

`ArticleRenderContent`, `ArticleOnward`, `onward.ts` and `origin.ts` take
`Project` today. They take a `Container` —
`{ kind: "project"; project } | { kind: "author"; author: PublicUserProfile }`
— and the two route files build it: `app/projects/[slug]/articles/[articleSlug]/`
as now, and the new `app/users/[id]/articles/[articleSlug]/`. The author
branch renders name and avatar where the project branch renders icon and
title, "More from {name}" for the heading, and the Follow button targets the
user. The shared files move to `app/articles/` alongside the editor so both
routes import from one place.

### Readers that print the project

| Reader | Today | Change |
|---|---|---|
| `ArticleOut.project`, `UserArticleResponse.project` | required | `| None`; `author` already present |
| `FeedArticleRef` | `project_slug`, `project_title: str` | `project_title: str | None`; add `author_id`, `author_name`, `author_avatar_url` |
| `NotificationGroup.project` | required | `| None`; add `author`; `lib/notifications.ts` deep-links by whichever is set |
| `article_digest.py` `_article_url`, byline, icon | project | author URL `/users/{id}/articles/{slug}`, author name and avatar, no icon |
| `apps/feed/models.py:51` | `article__project__status = approved` | `article__project__isnull = True \| …approved` |
| `services/users/django_impl/query.py:131` | `project__status = approved` | same disjunction |
| `assign_unique_article_slug` | scope `project_id` | scope `project_id`, or `(author_id, project__isnull=True)` |
| listing-image check | `image.project_id == article.project_id` | `image.article_id == article.id`, or the project match when there is a project |
| `_reserve` storage key | `projects/{project_id}/…` | `articles/{article_id}/…` when there is no project; `generate_article_upload_key` beside the avatar one |
| `Article.__str__`, `Channel.__str__`, `Image.__str__`, admin columns | `.project.title` | null-safe, author name as fallback |

### The owner's article list reuses the my-projects badges

`GET /api/auth/me/articles` returns `UserArticleResponse` plus `state` and
`global_visibility` for every article the caller authored, both kinds.
`articleBadge` and `sortDraftsFirst` move out of `MyProjectArticles.tsx` into
`lib/article-listing.ts` and the profile page renders the owner's list with
them when `profile.id === user.id`. The "waiting for review" gap from
`docs/2026-08-19-article-launch-followups.md` is closed for author-owned
articles by the same badge the project tab already shows.

### Author deletion deletes author-owned articles

Two owner-aware `on_delete` callables in `apps/articles/models.py`:
`Article.author` cascades an author-owned article and sets null on a project
one (the old `SET_NULL`); `Article.channel` protects a project's channel while
articles sit in it (the old `PROTECT`) and cascades a person's channel to their
articles. Without the first, `SET_NULL` would produce a row with no project and
no author, which the check constraint rejects. Without the second, the account
could not be deleted at all: `Channel.owner` cascades to the personal channel,
whose `PROTECT` the collector raises on before any `pre_delete` receiver runs —
which is why this is not the `pre_delete` receiver on `User` first planned.
Images and notifications cascade from the article as today.

## Risks / Trade-offs

- [The rename touches 25 backend files and ~13 frontend files] → first task,
  own commit, nothing else in it; `make lint` on both sides is the check.
- [Dropping the `follow__project_id` filter from the fan-out] → a
  `FollowedChannel` can only reference a channel of its follow's target
  because the handlers are the only writers; a test asserts a project follower
  is not delivered a person's article and vice versa.
- [`AlterModelTable` on `project_images`] → Postgres rename is metadata-only;
  the FK columns on `articles.listing_image_id`, `image_variants`,
  `project_images.article_id` follow automatically. No raw SQL names the table.
- [Breaking internal routes while the web-ui and backend deploy from one
  pipeline] → both halves land in one PR; an old browser tab holding the
  previous editor URL hits the redirect.
- [`/api/auth/me/articles` lives in the auth router] → precedent is
  `/me/avatar`; the alternative under `/api/users/me` would need to be
  registered ahead of `{user_id: UUID}` and read as a trick.
- [The spec lets `channel` be a project's channel on an article with no
  project only by handler rule, not DB constraint] → the check constraint
  cannot join to `channels.project_id`; `update_article` rejects `channel_id`
  on an author-owned article and `publish` is the only writer of the personal
  one.
- [The user-profile-page change is unarchived, so its spec is not in
  `openspec/specs/`] → archive it before this change lands; the two
  requirements that loosen (articles list with project; who sees the list)
  are restated in `author-articles` and `user-following`.

## Migration Plan

Three migrations, additive, in dependency order, generated by
`makemigrations` and checked with `--check --dry-run`:

1. `projects`: `RenameModel ProjectImage → Image`, `AlterModelTable → images`,
   `project` nullable, check constraint. Existing rows satisfy it.
2. `follows`: `Channel.owner`, `Follow.followed_user`, drop the two
   `unique_together` in favour of four `UniqueConstraint`s (two per model, one
   per target) and the check constraints. Existing rows satisfy them.
3. `articles`: `project` and `channel` nullable, the partial unique on
   `(author, slug) where project is null`, the existing `(project, slug)` one
   narrowed to `project is not null`, the project-implies-channel check.

Rollback is the reverse migrations. Author-owned rows written after deploy
would violate `NOT NULL` on reversal; none exist before it. Backend and web-ui
ship together; `make extract-openapi` and the committed `backend-openapi.json`
are the contract between them.

## Open Questions

- Whether a person's channel is ever shown by name anywhere. The constant is
  hidden in the two places a channel name renders today; if a later surface
  wants it, "Articles" is a placeholder and the constant is one line.
