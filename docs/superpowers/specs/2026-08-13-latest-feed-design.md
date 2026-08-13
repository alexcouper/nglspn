# Latest Feed — Design

Date: 2026-08-13
Status: design (pre-implementation)

Supersedes the `/news` half of Phase 5 in
[2026-05-13-articles-following-news-design.md](2026-05-13-articles-following-news-design.md).
That phase proposed a separate `/news` destination plus a "Latest News" carousel
on Discover. Neither shipped, and neither survives contact with the actual
publishing rate.

## Why this exists

Articles shipped (Phases 1–3 of the earlier design). They are only reachable
from the project that published them, so nobody sees one unless they already
follow that project. Before announcing the feature there has to be somewhere to
browse them.

## The constraint that decides everything

**0–3 articles per week, platform-wide.** At that rate:

- A dedicated `/news` destination is a ghost town, and a carousel of six article
  cards is padded most weeks.
- An article is an *event*, not a feed item. It deserves prominence when fresh
  rather than a permanent row.
- Articles alone cannot answer "what's changed since I was last here" — the
  front page's job, since `/` redirects to `/projects` and the traffic is
  returning regulars. New projects, tipoffs and competition milestones have to
  be in the same stream to make it worth visiting.

## Shape

A **Latest** tab, first in the existing sticky tab bar
(`src/web-ui/src/app/projects/CategoryTabs.tsx`), at `/latest`. That tab bar is
currently rendered by `ProjectsPage` and has to become shared chrome, so
`/latest` and `/projects` show the identical bar and moving between them costs
one click.

Discover remains the default landing view in this iteration. Latest is purely
additive, so nothing regresses; promoting it to the default is a separate,
reversible decision to make after reviewing it with real content.

Discover is **not** touched. It keeps New Arrivals, Competition Winners and
Recent Tipoffs, which Latest also shows as events. The overlap is accepted for
one iteration — see [Deferred](#deferred).

## Entries are stories, not records

One row type, three fill levels. No layout anywhere needs an article-versus-event
special case.

| State | Renders | Links to |
|---|---|---|
| Bare event | Flag, title, date | The project or competition |
| Event + write-up | Event flag, article headline, image, standfirst | The article |
| Standalone article | Channel as flag, then as above | The article |

The write-up does not replace the flag — a winner write-up reads
"Competition winner · Chili" above the article's own headline. The event is what
gives the article its context.

### Sources

Automatic:

- Published article, any project, any channel
- New project published
- Community tipoff
- Competition milestone — opens, closes, winners announced

Deliberate:

- **Promoted discussion.** An admin pushes a thread into the feed when it's worth
  reading. Never automatic — discussion volume would turn the feed into a ticker
  and drown three articles a week. This is a new admin surface with no existing
  home.

### Superseding

An article *about* an event appends its own event and **supersedes** the earlier
one, which is then not rendered. One story, one row, always — the feed never
shows "Broadside wins Chili" and "How Broadside won Chili" as two entries.

- Superseding is one-shot. A *second* article about the same competition is its
  own entry, not another supersede.
- A superseded event is retired, not deleted, so it stays possible to explain
  why a row sits where it does.

## Ordering

**Append-only stream, ordered strictly by event time.** Nothing already in the
stream changes position.

This is why the write-up appends-and-supersedes rather than re-dating the
original event: a mutable sort key breaks cursor pagination, because an entry
that moves can cross a cursor boundary between page fetches and be served twice
or skipped. An immutable event time gives a stable cursor and cheap
`occurred_at < ?` paging.

Editing an article is not a problem for this. A row references its article and
renders whatever the article currently says — an edit changes *content*, not
*position*, and only position breaks paging.

Week headers are the only grouping.

## The lead

The top story renders full width — image, headline, standfirst — **only if its
article is recent** (roughly a week; tune on real content). Otherwise the feed
starts flat.

There is no hero slot. The promotion is a property of freshness, so it expires
on its own and cannot go stale through neglect — which matters, because the
existing Featured section already demonstrates what an unattended curated slot
looks like. An admin pin overrides the rule but is not the mechanism.

## Mobile

The same list, single column. The lead card goes full width; thumbnails stay
left. Nothing in the layout depends on a wide viewport — a right-hand activity
rail was considered and rejected for exactly this reason.

## Empty state

Not reachable in practice: new projects and tipoffs keep the stream populated
even in a fortnight with no articles. If the stream is genuinely empty, show a
short line and a link to Discover rather than an illustration.

## Copy

Labels are English, matching the rest of the web UI ("New Arrivals",
"Competition Winners", "Submit a project"). The tab reads **Latest**.

## Deferred

- **Discover's overlap with Latest.** Discover will show new arrivals, winners
  and tipoffs that Latest also carries. The intended resolution is to strip
  Discover to what a timeline cannot express — featured picks, an all-time
  winners shelf, most-discussed — and to drop the four category rows, which
  duplicate the sticky tabs directly above them. Not this iteration.
- **Latest as the default landing view.**
- **Per-project domination caps.** The earlier design capped a project at two
  articles in the Discover carousel. At 0–3 articles a week a cap is solving a
  problem that does not exist, but it is the first thing to add if volume climbs.
- **`/news` as a URL.** Superseded by the tab.

## Risks

1. **Promoted discussions have no admin surface.** Small, but not free, and it
   is the only part of this design that adds an operator workflow.
2. **The lead's freshness window is a guess.** A week is chosen against a
   0–3/week rate. If publishing accelerates, the window should shorten or the
   lead will churn daily.
3. **Superseding depends on knowing an article is about an event.** The link has
   to be established somewhere — most plausibly at publish time — and if it is
   missed, the feed shows the duplicate pair this design exists to avoid. The
   failure is visible and recoverable, but it is a manual step that can be
   skipped.
4. **Discover and Latest disagree for one iteration.** Two adjacent tabs both
   answer "what's new", and the newer one is better at it. Tolerable briefly;
   corrosive if it becomes permanent.
