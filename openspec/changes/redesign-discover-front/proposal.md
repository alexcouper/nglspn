# Redesign the Discover front page

## Why

`/` redirects to `/projects`, and the top of that page is three admin-picked
projects. None of the site's articles appear on it (#102). The layout agreed in
[`docs/2026-10-14-discover-redesign.md`](../../../docs/2026-10-14-discover-redesign.md)
(#110) replaces them with the newest writing, the competition that wants action
now, and the house's spotlighted pieces. This change is the plan for building it,
including the points where the build departs from that doc. They are listed in
[design.md](design.md#departures-from-the-design-doc).

## What Changes

- **Recent**: the two newest front-page articles from anyone, plus a
  competition slot, in the existing 1 + 2 grid at the top of Discover.
- **Competition slot**: a round in voting, otherwise one open for entries,
  otherwise the last closed round with its winner. It is drawn as state plus
  a verb, not as an article.
- **In the spotlight**: articles an admin has flagged, minus those already in
  Recent, up to three.
- **`Article.is_spotlight`** and **`Article.recent_until`**: both admin-only.
  The first puts an article in the spotlight. The second takes an article out
  of Recent and "read next" once a notice (such as "voting open until …") is
  out of date.
- **`GET /api/articles/recent`** and **`GET /api/articles/spotlight`**: new
  public endpoints.
- **Competition highlights carry the winner** on a closed round.
- **Article "read next"** draws on recent articles instead of the feed, and
  its "more" link goes to Discover.
- **BREAKING (UI)**: the Latest page and tab are removed. `/latest`
  redirects permanently to `/projects`, and `?from=latest` article links
  fall back to the article's project or author.
- **BREAKING (API)**: `GET /api/feed` is removed and so is `GET
  /api/projects/featured`, together with the `feed_events` table and the
  `Project.is_featured` column. Both columns' data is dropped, so this
  ships in a second PR, after the first is deployed.

## Capabilities

### New Capabilities

None. The front page is the Discover view, already specified by
`project-listing-discover`.

### Modified Capabilities

- `project-listing-discover`: the Featured section and its endpoint are
  replaced by Recent, the competition slot and the spotlight, and their
  endpoints.
- `articles`: adds the spotlight flag, the Recent expiry and "read next". The
  feed is dropped from the read-path gate. Publishing no longer appends a feed
  event.
- `author-articles`: front-page cards replace the Latest row in the list of
  surfaces that show the author.
- `competition-highlights-carousel`: a closed competition in the highlights
  carries its winner.
- `project-listing-category-view`: the tab bar loses its Latest tab.
- `project-page-layout`: `is_featured` is removed.
- `latest-feed`: every requirement is removed. The capability ends.

## Impact

**Backend** (`src/django-backend/`):
- `apps/articles`: two fields, a migration and a data migration, plus admin.
- `api/routers/article_items.py` and `api/schemas/article.py`: the two
  endpoints.
- `api/schemas/competition.py`: the winner on `CompetitionSummaryResponse`.
- PR 2 deletes `apps/feed`, `services/feed`, `api/routers/feed.py`, the
  feed action in `apps/discussions/admin.py`, `Project.is_featured`,
  `list_featured` and `GET /api/projects/featured`.
- *Migrations* in both PRs. *OpenAPI regeneration* in both PRs.

**Frontend** (`src/web-ui/`):
- `app/projects/`: new sections. `FeaturedSection` goes, but
  `LargeHeroCard` moves to `components/` because `ImageRoleDialog` uses it
  as a preview.
- `app/latest/`, `lib/api/feed.ts` and `i18n/feed/` are deleted.
- `ListingTabs`, `sitemap.ts`, `next.config.ts` (the redirect), and
  `articles/onward.ts` / `origin.ts` with both article pages.
- `e2e/author-article.spec.ts` and `e2e/leave-guard.spec.ts` load `/latest`
  and have to move.

**Data**: production has 0 pinned feed entries and 0 promoted discussions as
of 2026-11-25. Retired entries can't be seen through the API and are checked
before PR 1 deploys (tasks 5.3).
