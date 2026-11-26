# Design

## Context

The layout and its rationale are in
[`docs/2026-10-14-discover-redesign.md`](../../../docs/2026-10-14-discover-redesign.md).
This file records how it is built and where the build departs from that doc.
The departures were settled on 2026-11-25 against production data from that day.

Today `projects/page.tsx` server-fetches five Discover sources in one
`Promise.all` and passes them to `DiscoverView`. Articles reach the public only
through project and profile listings, `GET /api/feed` (the Latest page), and
"read next" on the two article pages, which tops up from the feed's first page
(`app/articles/onward.ts`).

## Departures from the design doc

| Doc says | Built as | Why |
|---|---|---|
| Recent ordered by `published_at` | `approved_at`, falling back to `published_at` | `published_at` can be edited after publishing, so an author could put their article back on top. A late approval would also never reach Recent. |
| Recent filtered by `globally_visible()` | That filter, plus approved project, `published_at` in the past, and `recent_until` | The feed already filters out unapproved projects and scheduled articles. Dropping those checks would expose them. |
| Recent has no expiry | `Article.recent_until`, set in admin | #102's core complaint: "voting open" notices stayed on top after voting closed. |
| — | No age limit on Recent | An age limit would leave holes in the grid when writing is slow (20 days between articles before 25 Nov). The card's date shows the reader how old it is. |
| Slot 3: accepting, then voting, then closed | Voting (if not past its end date), then accepting, then closed with a winner | The next round opens on the day the previous one closes. With the doc's order, voting would never show. |
| Spotlight with note, "All reviews" link, stripped titles | Heading only, standard flag, full title | There is no reviews page to link to, and the note stops being true once something other than a review is spotlighted. |
| Spotlight flag set on 4 articles | Every visible house `Reviews` article (7 on 2026-11-25) | More reviews have been published since then. |
| Card items carry project slug and title | Also the author's id, name and avatar | Author-owned articles (#112) landed after the doc. |
| "Nothing reads `GET /api/feed` except Latest" | "Read next" reads it too, and moves to the recent endpoint | #111 and #112 landed after the doc. |
| Lift `FeedRow`'s image into a shared `ListingImage` | Already exists as `ArticleListingImage` | — |
| Four PRs | Two | See Migration Plan. |
| Drops `feed_feedevent` | The table is `feed_events` | — |

## Goals / Non-Goals

**Goals:** see the specs. Below the spotlight, the Discover view is unchanged.

**Non-Goals:**
- The Opinion tier.
- A site-wide article archive. The house project's Articles tab is the
  archive for now.
- Changes to `CompetitionHighlight` on `/about/prizes`.
- Icelandic copy. Only `en.json` is added.

## Decisions

**One queryset method for front-page eligibility.** `ArticleQuerySet.on_front_page()`
applies `globally_visible()`, the project-approved check, the past
`published_at`, and annotates and orders by `Coalesce("approved_at",
"published_at")`. The recent query adds the `recent_until` filter and the
spotlight query adds `is_spotlight=True`. Both go through `REPO.articles`,
like the other read paths. Keeping eligibility in one method means the two
endpoints can't apply different visibility rules.

**A new response schema, `FrontPageArticle`.** `ArticleListItem` carries
editor-only visibility fields and no project or author, and `UserArticleResponse`
has no author. The new schema has the fields listed in the spec. Its image is
`variant_url(listing_image, "large")`, which falls back to the original.
`listing_crop` is normalised, so it applies to a variant unchanged. Considered
and rejected: widening `ArticleListItem`, which would leak author fields into
the project listing's contract.

**Where the endpoints live.** `GET /api/articles/recent` and `/spotlight` sit on
the `article_items` router, registered before `/{article_id}`, with
`auth=None`. A router test asserts that `recent` is not taken for an article
id. `limit` is clamped to 1–10.

**A winner on `CompetitionSummaryResponse`.** It is a nullable `winner` object
(slug, title, image URL), filled only for closed competitions.
`get_highlights` adds `select_related("winner")` and
`gallery_prefetch("winner__images")`. The image follows `list_winners`'
resolution order: hero banner (large), then in-use image (medium). This adds
one prefetch query, not one query per competition.

**The front of the page is chosen by one pure function.**
`src/lib/discover-top.ts` exports `selectDiscoverTop({ recent, spotlight,
competitions, today })` and returns `{ lead, second, slot, spotlight }`. `slot`
is a union keyed by state, so each card branch is told which state it is in.
All the rules in the spec live here and are tested here. The components only
lay out what it returns. `today` is passed in so the deadline rule can be
tested.

**Components.**
- The lead and the spotlight cards reuse `ArticleCard` (variants `lead` and
  `grid`) with `flag`.
- The small top-right card is a new `variant="overlay"` on `ArticleCard`.
  Without an image it falls back to the `grid` layout, so the text-led rule
  stays in one component.
- `CompetitionSlot` is new. It reuses `getCompetitionDeadline`,
  `CompetitionStatusBadge`'s colours, and `competitions.highlight`'s plural
  messages where the wording matches.
- Mobile order uses CSS `order` on a single grid, not duplicated markup.

**Fetching.** `projects/page.tsx` adds `fetchRecentArticles()`,
`fetchSpotlightArticles()` and `fetchCompetitionHighlights()`, each followed by
`.catch(() => null)`. `null` means the section is hidden. The existing four
fetches are not changed.

**"Read next" and origins.** `onward.ts` takes `recent: FrontPageArticle[]` in
place of `feed: FeedEntry[]`, and `feedArticleHref` becomes
`frontPageArticleHref`. Both article pages call `fetchRecentArticles(6)` when
the container is thin; 6 covers the slots after the current article and its
container are excluded. `OnwardMore`'s `latest` becomes `discover` →
`/projects`. `ORIGINS` swaps `latest` for `discover`.

**The redirect.** A `redirects()` entry in `next.config.ts`, `/latest` →
`/projects`, `permanent: true`. It is declared there rather than kept as a
route file, so `sitemap-coverage.test.ts` has nothing to account for.

**The feed table is dropped without an export.** The doc asked whether to
export pin, retire and promote state first. Production had 0 pinned entries
and 0 promoted discussions on 2026-11-25, and the stream itself can be rebuilt
with `backfill_feed`. Only retired entries are unknown, and task 5.3 deals with
those before Recent goes live. There is nothing else worth keeping.

**Retiring `apps.feed` in two steps (PR 2).** Django cannot apply a migration
that belongs to an app that is no longer installed. PR 2 therefore keeps
`apps/feed/` with only `apps.py`, its migrations, and a new migration that
deletes `FeedEvent`. Everything else in the app goes. Deleting the directory
and its `INSTALLED_APPS` line is a follow-up, once production has applied the
migration. `is_featured` is an ordinary `RemoveField`.

## Risks / Trade-offs

- **A retired feed entry may hide an article that would appear in Recent.**
  Retiring is the only feed curation production may hold, and Recent ignores
  it. → Task 5.3 checks before PR 1 deploys, and `recent_until` handles any
  match.
- **Nobody sets `recent_until`.** The setting is manual, so a forgotten notice
  stays up until two newer articles push it down. → It is one admin field, and
  the competition slot gives the live state either way.
- **The spotlight relies on someone remembering to flag.** This was decided
  (Q5). The spotlight shrinks rather than going stale.
- **Dropping columns while old pods are still running.** A rolling deploy of
  PR 2 runs old code against a migrated schema. → PR 1 removes every reader
  first. PR 2 deploys only after PR 1 is live and nothing reads `is_featured`
  or `feed_events`.
- **Losing the only site-wide article list.** With 16 articles, all on the
  house project, its Articles tab covers it. Revisit if community writing
  grows.

## Migration Plan

1. **PR 1 (additive).** Add `is_spotlight` and `recent_until`, with a data
   migration flagging the house Reviews. Add the endpoints and the winner
   field. Build the new page, drop Latest, and redirect.
   *Rollback:* revert. The two new columns are harmless to old code.
2. After deploy, set `recent_until` on any live "voting open" article in
   admin.
3. **PR 2 (destructive)**, once PR 1 is live: remove `apps.feed` except its
   migrations (with a `DeleteModel` migration), and remove `is_featured` and
   its endpoint. *Rollback:* restore from backup. The feed can be rebuilt with
   `backfill_feed` from the PR 1 tree, but its retire and pin state is lost.
4. **Follow-up:** delete `apps/feed/` and its `INSTALLED_APPS` entry.
