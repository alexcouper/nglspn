# Tasks: redesign the Discover front page

Backend paths are relative to `src/django-backend/` and frontend paths to
`src/web-ui/`. Groups 1–5 are **PR 1**. Groups 6–7 are **PR 2**, opened only
once PR 1 is deployed (see [design.md](design.md#migration-plan)).

## 1. PR 1 — Article fields and admin

- [x] 1.1 Add `Article.is_spotlight` (bool, default false) and
  `Article.recent_until` (nullable datetime), each with a one-line comment
  saying who sets it and what it does. Write the migration, and verify with
  `uv run python manage.py makemigrations --check --dry-run`.
- [x] 1.2 Data migration: set `is_spotlight` on every globally visible
  article in the channel named `Reviews` on the project with
  `is_house_project=True`, using historical models. A no-op if there is no
  house project. Test it with a migration test in the style of
  `apps/projects/test_prune_reviews_migration.py`: a house Review gets the
  flag; a draft, a Review on another project and an Updates article don't.
- [x] 1.3 `ArticleAdmin`: add a "Front page" fieldset (`is_spotlight`,
  `recent_until`), `is_spotlight` in `list_display`, `list_editable` and
  `list_filter`. Check in the local admin that toggling from the list saves.

## 2. PR 1 — Front-page endpoints and the competition winner

- [x] 2.1 Add `ArticleQuerySet.on_front_page()` (see design: visible,
  author-owned or on an approved project, `published_at` in the past, ordered
  by `Coalesce(approved_at, published_at)` descending), plus `REPO.articles`
  methods `recent(limit)` (adds `recent_until` null or in the future) and
  `spotlight(limit)` (adds `is_spotlight`). Select and prefetch everything the
  schema reads. Cover each spec scenario under "Front-page articles" with
  query tests, using factories and an assertion helper on the returned ids.
- [x] 2.2 Add a `FrontPageArticle` schema in `api/schemas/article.py`: the
  card fields from the spec, with the image from `variant_url(...,
  "large")`.
- [x] 2.3 Add `GET /api/articles/recent` and `GET /api/articles/spotlight`
  to `api/routers/article_items.py` with `auth=None`, registered before
  `/{article_id}`. `limit` defaults to 2 and 5 and is clamped to 1–10.
  Router tests cover: anonymous access; order; author-owned shape; expired
  `recent_until` excluded from recent but kept in spotlight; the clamp;
  `recent` not read as an article id; a query-count bound, so card fields
  don't cost one query per article.
- [x] 2.4 Add a nullable `winner` (slug, title, image URL) to
  `CompetitionSummaryResponse`, set only for closed competitions with a
  winner. In `get_highlights`, add `select_related("winner")` and
  `gallery_prefetch("winner__images")`. Router tests cover: closed with a
  winner, closed without one, active rounds with null, and a query-count bound.
- [x] 2.5 Run `make extract-openapi` and commit `backend-openapi.json`, then
  `make lint`, `make extra-tests` and `make test` in the backend.

## 3. PR 1 — The new top of Discover

- [x] 3.1 `npm run generate-types`. Add `fetchRecentArticles(limit)` and
  `fetchSpotlightArticles(limit)` to `lib/api/server.ts`, and export a
  `FrontPageArticle` type from `lib/api`.
- [x] 3.2 Write `src/lib/discover-top.ts` (`selectDiscoverTop`) test-first, in
  `discover-top.test.ts` with factory helpers for articles and competitions.
  Cases: two recent plus a slot; one recent; none; spotlight duplicates
  removed by id; spotlight capped at 3; nothing left after removing
  duplicates; voting beats accepting; voting past its end date skipped;
  accepting only; closed with a winner; closed without a winner gives no slot;
  no competitions; `null` inputs (a failed fetch) treated as empty.
- [x] 3.3 Move `LargeHeroCard` out of `sections/FeaturedSection.tsx` into
  `components/ProjectHeroCard.tsx` and update `ImageRoleDialog`. Verify that
  `make lint` passes and the image-role dialog preview still renders.
- [x] 3.4 Render the top-right Recent card as a `grid` `ArticleCard`. A
  `variant="overlay"` was added for it and removed again in review, with its
  tests.
- [x] 3.5 Build `CompetitionSlot` for its three states, linking to
  `/competitions/{slug}`. Reuse `getCompetitionDeadline` and the status
  colours. Write a test per state asserting the label, verb, days left and
  winner, using the English messages.
- [x] 3.6 Build `RecentSection` (1 + 2 grid, the no-slot and one-article
  layouts, and mobile order lead → slot → second via CSS `order`) and
  `SpotlightSection` (up to three `grid` cards, heading only). Cards link with
  `?from=discover`. Test the layouts with one, two and no articles.
- [x] 3.7 Wire `projects/page.tsx` → `ProjectsPage` → `DiscoverView`: add the
  three fetches with `.catch(() => null)`. Drop `fetchFeaturedProjects` and
  the `featured` prop, and delete `FeaturedSection.tsx`. Verify `npm run
  build` succeeds.
- [x] 3.8 Put the strings in `i18n/projects/en.json` under `recent.*`,
  `spotlight.*` and `competitionSlot.*`, with ICU plurals for days and
  entries. Verify `make lint`: the `no-hardcoded-ui-strings` rule passes with
  no new line in `i18n-pending.mjs`.

## 4. PR 1 — Retire Latest

- [x] 4.1 "Read next": switch `articles/onward.ts` from `FeedEntry` to
  `FrontPageArticle`. Rename `feedArticleHref` to `frontPageArticleHref`, and
  `OnwardMore` `latest` to `discover` → `/projects`. Both article pages call
  `fetchRecentArticles(6)` instead of `fetchFeedPage()`. Update
  `onward.test.ts` and `article-render.test.tsx`, and the `articles` i18n key
  for the "more" link.
- [x] 4.2 `articles/origin.ts`: replace `latest` with `discover` →
  `/projects`. Update `origin.test.ts`, including a case that `?from=latest`
  now falls back to the container.
- [x] 4.3 Delete `app/latest/`, `lib/api/feed.ts` with its `api.feed` client
  entry, `fetchFeedPage`, `i18n/feed/` and its line in `i18n/messages.ts`, and
  `projects.listingTabs.latest`. Remove the `latest` tab and `ListingTab` kind
  from `ListingTabs`, and update its comment. Leave
  `use-leave-guard.test.tsx`'s `/latest` hrefs alone: they are arbitrary
  links.
- [x] 4.4 Remove `/latest` from `PUBLIC_STATIC_PAGES` in `sitemap.ts`. Add
  the permanent redirect `/latest` → `/projects` in `next.config.ts`. Verify
  with `make test` (sitemap coverage) and `curl -sI localhost:3000/latest`
  showing a 308 to `/projects`.
- [x] 4.5 e2e: `author-article.spec.ts` checks V sees U's article in Recent on
  `/projects` instead of Latest. `leave-guard.spec.ts` opens `/projects` and
  waits for a Discover link instead of a feed row. Run both against a local
  stack.
- [x] 4.6 Run `make lint`, `make test`, `make build-app` and `make
  extra-tests` (bundle budgets) in the web-ui.

## 5. PR 1 — Docs, end-to-end check, deploy

- [x] 5.1 Add one line to `docs/2026-10-14-discover-redesign.md` pointing to
  this change for where the build departs. In
  `docs/2026-08-19-article-launch-followups.md`, correct the parts that assume
  the Latest feed.
- [x] 5.2 With both services and `make seed` running, sign in through
  Playwright and check `/projects` at 1280px and 390px:
  - Recent appears with the slot, and the stacked order is correct.
  - The spotlight has no duplicates.
  - A card without an image is text-led.
  - Ticking `is_spotlight` and setting `recent_until` in admin each show on
    reload.
  - `/latest` redirects.
  - The back control from a Discover card returns to `/projects`.
- [ ] 5.3 Before deploy, list production feed entries that are retired but
  whose article is still visible (`FeedEvent.objects.filter(retired_at__isnull=False,
  article__isnull=False)` on visible articles). For each, decide on
  `recent_until` with the user. Record the result in the PR.
- [ ] 5.4 Open PR 1 using the repo template, referencing #102.

## 6. PR 2 — Remove the feed

- [ ] 6.1 Add an `apps/feed` migration that deletes `FeedEvent`. Then delete
  everything in `apps/feed` except `apps.py`, `__init__.py` and `migrations/`.
  That includes the model, signals, admin, the `backfill_feed` command and
  tests; `FeedConfig.ready()` no longer imports signals. Verify with
  `makemigrations --check` and a migrate on a copy of the seeded database.
- [ ] 6.2 Delete `services/feed/` and its registration in `services/__init__.py`,
  `api/routers/feed.py` with its mount and `test_feed.py`,
  `api/schemas/feed.py`, the `FEED_LEAD_FRESHNESS_DAYS` setting, the
  "Promote to the Latest feed" action in `apps/discussions/admin.py`, and the
  `FeedEvent` use in `tests/test_project_emails.py`. Edit the
  `globally_visible_q` docstring that names the feed. Verify with
  `grep -rn "feed" --include=*.py` and review what is left.

## 7. PR 2 — Remove `Project.is_featured`

- [ ] 7.1 Remove the field (with a migration), the admin column, list-editable
  and actions, `list_featured` from the query interface and implementation,
  `GET /api/projects/featured`, the `featured` key in
  `seed_discover_data.py`, and the `is_featured` cases in
  `api/routers/test_discover.py`. Remove `fetchFeaturedProjects` in the web-ui
  if task 3.7 left it.
- [ ] 7.2 Run `make extract-openapi`, commit the spec, and confirm
  `npm run generate-types` and `make lint` pass in the web-ui with nothing
  referencing the removed types. Then run `make lint`, `make extra-tests` and
  `make test` in the backend.
- [ ] 7.3 Open PR 2 and note that it requires PR 1 in production.

## Workflow follow-up

- Once production has applied the PR 2 migration, delete `apps/feed/` and
  its `INSTALLED_APPS` line.
- Archive this change after PR 2 merges. That syncs the deltas, including
  the removal of `latest-feed` and the move of the tab bar and
  `project-listing-discover` specs.
