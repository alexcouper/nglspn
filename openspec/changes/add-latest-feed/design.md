## Context

`/` redirects to `/projects`, so the project listing page is the front door, and
its traffic is returning regulars. The page is currently six carousels of equal
weight — Featured, New Arrivals, Competition Winners, Recent Tipoffs, Most
Discussed, plus four category rows that duplicate the sticky tabs directly above
them. There is no hierarchy left to give a new section.

Articles landed via Phases 1–3 of
[2026-05-13-articles-following-news-design.md](../../../docs/superpowers/specs/2026-05-13-articles-following-news-design.md).
Phase 5 of that document proposed a `/news` page plus a Discover carousel; it
never shipped and this change replaces it.

The binding constraint is volume: **0–3 published articles per week,
platform-wide**. Every decision below follows from it.

## Goals / Non-Goals

**Goals:**

- A surface where a visitor can see what has happened on the platform, articles
  included, without already following anything.
- A home worth linking to from the feature announcement.
- Never look abandoned in a fortnight with no articles.
- Ship additively: nothing existing changes behaviour.

**Non-Goals:**

- Changing Discover, including the category rows that duplicate the tabs.
- Making Latest the default landing view.
- Per-project domination caps.
- Personalisation. The feed is identical for everyone, signed in or not.
- Comments or reactions on feed entries.

## Decisions

### A tab, not a destination

**Decision:** Latest is a tab in the existing sticky bar at `/latest`, not a
separate `/news` page.

*Alternatives considered.* A **masthead** on Discover — a lead story plus two
secondaries above the existing carousels — is the smallest change and degrades
to today's page when nothing is fresh, but only the top of the page changes and
"what's new" stays scattered across the rows below. An **activity rail** down
the right of Discover is always visible and never empty, but a right rail
collapses to a bottom block on mobile, which is where it is worth least. A
separate `/news` **destination**, as Phase 5 proposed, has to be navigated to
deliberately and at this volume rewards the trip about once a fortnight.

The tab bar already exists and already carries the "these are peer views of the
same place" meaning. Using it costs one component extraction.

### The feed mixes articles with platform events

**Decision:** the stream carries published articles, new projects, community
tipoffs and competition milestones automatically, plus discussions an admin
promotes.

*Alternative considered.* An **articles-only** feed is the purest reading of
"just a feed" and needs only a cross-project article list. It was rejected on
the quiet-fortnight case: two thirds of the time the tab would hold one item
over a week old, which reads as abandoned. Mixing in project and competition
events puts the weekly count in the teens without inventing anything.

Discussion activity is the one source deliberately left manual. It is the
highest-volume, lowest-signal event available, and automatic inclusion would
drown three articles a week in thread noise.

### Entries are stories, not records

**Decision:** one row type with three fill levels — bare event, event plus
write-up, standalone article. An article about an event supersedes that event's
entry.

This is what keeps the layout free of article-versus-event special cases, and it
stops the feed showing "Broadside wins Chili" and "How Broadside won Chili" as
two rows. The event survives as the flag above the article's headline, because
the event is what gives the article its context.

Superseding is one-shot: a *second* article about the same competition is its own
entry. Without that rule, "supersede" has no well-defined target once more than
one article claims the same event.

### Append-only stream, ordered by event time

**Decision:** the stream is append-only and ordered strictly by event time.
Nothing already in it changes position. A late write-up appends its own event and
supersedes the earlier one; it does not re-date it.

*Alternative considered.* Sorting by **last change** — so an upgraded entry
resurfaces — produces the same visible result and was the initial proposal. It
was rejected because a mutable sort key breaks cursor pagination: an entry that
moves can cross a cursor boundary between page fetches and be served twice or
skipped. Caching has the same problem, where any edit invalidates an unknown
slice. An immutable `occurred_at` gives a stable cursor and cheap
`occurred_at < ?` paging.

Allowing article edits does not undermine this. A row references its article and
renders whatever the article currently says — an edit changes *content*, not
*position*, and only position breaks paging.

A superseded event is retired rather than deleted, so it stays possible to
explain why a row sits where it does.

### The lead is freshness-gated, not curated

**Decision:** the top story renders full width only when its article was
published within a freshness window (start at 7 days). Otherwise the feed starts
flat. An admin pin overrides the rule but is not the mechanism.

*Alternative considered.* A **curated hero slot** looks best and was rejected
because it needs attention every week to stay honest — and the existing Featured
section already demonstrates what an unattended curated slot looks like. A
freshness-gated promotion expires by itself, so neglect produces a plain feed
rather than a stale headline.

### Competition gains a winner-announced timestamp

**Decision:** add `winner_announced_at` to Competition, set when a winner is
first assigned, and backfill it from `voting_end_date`.

Found while implementing. `Competition` carries `start_date`,
`submission_deadline` and `voting_end_date` as `DateField`s, and assigning a
winner flips `status` to `CLOSED` in `save()` without recording a time. The feed
needs a timestamp for its headline event type and there was none.

*Alternatives considered.* Deriving the event time from `voting_end_date`
directly needs no migration, but places the announcement on the voting deadline
rather than when it happened — often days apart, and wrong in a feed whose whole
premise is chronology. `updated_at` is closer for recent competitions but moves
on any edit, so a re-run of the idempotent backfill after an unrelated tweak
would relocate the event.

Date fields convert to datetimes at midnight for event purposes. That is
imprecise for backfilled history and exact for anything announced from here on,
which is the right way round.

### Copy stays English

Labels are English, matching the rest of the web UI — "New Arrivals",
"Competition Winners", "Submit a project". The tab reads **Latest**. This is a
statement of fact about the existing UI, not a decision to revisit here.

### Discover is left alone

**Decision:** no change to Discover in this change, accepting that both tabs
will show new arrivals, winners and tipoffs.

The intended eventual resolution is to strip Discover to what a timeline cannot
express — featured picks, an all-time winners shelf, most-discussed — and drop
the four category rows. Deferred deliberately to keep this change additive and
reviewable.

## Risks / Trade-offs

- **Superseding depends on someone linking article to event, and only an admin
  can.** A missed link produces exactly the duplicate pair this design exists to
  prevent. → Accepted. Offering the link to authors at publish time was the
  first plan and was dropped: superseding hides an entry from a site-wide feed,
  so an author could retire a competition or another project's arrival, and the
  publish API has no way to tell which events are theirs to touch. The link is
  set from admin, before or after publish. The failure mode is two entries where
  one would do — visible, harmless, and correctable — against a wrong link,
  which is none of those.

- **Two tabs disagree about "what's new" for one iteration**, and the newer one
  is better at it. → Tolerable briefly; the Discover strip is the intended
  follow-up and should not be allowed to drift indefinitely.

- **The 7-day freshness window is a guess** against current volume. If
  publishing accelerates, the lead churns daily. → Make the window a single
  configurable value, not a constant threaded through several components.

- **Promoted discussions add an operator workflow with no existing home.** → Keep
  it to a Django admin action rather than building a bespoke surface; it is a
  rare, deliberate act.

- **An append-only stream grows without bound and is written from five call
  sites.** → Retiring rather than deleting superseded rows compounds this. Index
  on `occurred_at` and keep the read path a single query; revisit retention only
  if the table becomes a problem, which at this event rate is years away.

- **Backfill is a judgement call.** An empty stream on launch shows nothing at
  all. → Seed from existing projects, tipoffs and competitions at their original
  timestamps, back to the earliest record with no cut-off, so the tab has real
  history on day one. Depth costs nothing to read: the feed is cursor-paginated
  from the start, so old entries sit behind paging rather than in the first
  response. This must not fire notifications — the same constraint that governed
  the Phase 4 content backfill.

- **Articles are out of the backfill's scope**, and as of 2026-08-14 no article
  has been published — the two that exist are drafts, held until this ships.
  They then go out through the normal publish path, so the backfill never has to
  reason about article state and no published article is left stranded. → If
  that turns out to be wrong, the backfill is idempotent: widening its scope to
  articles and re-running is a safe correction rather than a duplicate-producing
  one.

## Launch

The announcement goes out as an article on the house project — drafted already,
held until this ships. It is therefore the first lead the tab ever shows, and
the freshness rule gets exercised on real content from day one.

Order: ship the feed, run the backfill, then publish the pending drafts a few
days apart. Only the newest entry can lead, so publishing them together would
spend the second one's turn at the top.
