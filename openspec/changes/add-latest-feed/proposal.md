## Why

Articles shipped, but they are only reachable from the project that published
them — nobody sees one unless they already follow that project. There is nowhere
to browse them, so the feature cannot be announced.

At the platform's actual publishing rate (0–3 articles per week) a dedicated
news destination would be a ghost town and a carousel of article cards would be
padded most weeks. Articles need to arrive in a stream alongside the other
things that happen here.

## What Changes

- New **Latest** tab at `/latest`, first in the existing sticky tab bar,
  rendering an append-only stream of platform events.
- Feed entries are **stories, not records**: one row type with three fill levels
  — bare event, event plus write-up, standalone article.
- An article about an event **supersedes** that event's entry rather than adding
  a second row, so a competition winner and its write-up appear once.
- Automatic event sources: published article, new project, community tipoff,
  competition milestone (opens, closes, winners announced).
- Deliberate event source: an admin **promotes a discussion thread** into the
  feed. Never automatic.
- The top story renders full width only when its article is recent; the
  promotion expires on its own, so there is no curated hero slot to keep fed.
- The tab bar moves out of `ProjectsPage` into shared chrome so `/latest` and
  `/projects` render the identical bar.
- Discover is **not** changed. It keeps New Arrivals, Competition Winners and
  Recent Tipoffs, which Latest also surfaces as events. Discover also stays the
  default landing view; promoting Latest is a later, separate decision.

Not breaking: the change is additive, and no existing route or view changes
behaviour.

## Capabilities

### New Capabilities
- `latest-feed`: the Latest tab — the event stream, its entry states and
  sources, superseding, ordering and pagination, the freshness-gated lead, and
  the admin surface for promoting a discussion.

### Modified Capabilities
- `project-listing-category-view`: the "Category tabs bar" requirement gains a
  Latest tab ahead of Discover, and the bar becomes shared chrome rendered by
  both `/latest` and `/projects` rather than by `ProjectsPage` alone.
- `articles`: the publish flow gains an optional link from the article to the
  feed event it is about, which is what makes superseding possible.

## Impact

- **Frontend** — new `/latest` route; tab bar extracted from
  `src/web-ui/src/app/projects/ProjectsPage.tsx` into shared chrome; new feed
  row and lead card components. `ArticleCard` already covers the article-shaped
  entry and should be reused rather than duplicated.
- **Backend** — a new event stream: rows appended by article publish, project
  publish, tipoff, competition milestones, and admin promotion, plus a
  cursor-paginated read endpoint. Django admin gains the promote and supersede
  affordances.
- **Contract** — new endpoints mean `backend-openapi.json` must be regenerated
  and committed (see `CONTRIBUTING.md`).
- **Migrations** — new models for the stream; article publish gains the event
  link.
- **Docs** — this change is the plan of record. Phase 5 of
  `docs/superpowers/specs/2026-05-13-articles-following-news-design.md` is
  marked superseded and points here.
