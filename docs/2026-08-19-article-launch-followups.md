# Article launch follow-ups

What is left after articles, the Latest feed and the competition-entry work
shipped. Written while archiving the five OpenSpec changes that carried these
tasks — the plans are now under `openspec/changes/archive/`, and this file is
the only remaining home for the parts that were never done.

Several of these were written as *pre-deploy* steps and can no longer be done as
written. Production is at or past #82 (the Latest feed) — `backfill_feed` ran
against it on 2026-08-19. #83 (competition entry) and #80 (the channel merge)
are ancestors of #82, so both are deployed. Anything phrased "record this before
deploying" missed its window: one survives as a post-hoc check, one has been run
and recorded below, and one is simply gone.

## Still to do

**Stagger the pending article drafts.** The second half of
`add-latest-feed` task 8.4. The feed is live and the backfill has run, so the
stream has history; what it does not have is a run of published articles.
Publish the pending drafts a few days apart, house announcement first, so each
takes a turn as the lead story. The lead is freshness-gated and expires on its
own (`GET /api/feed`), so publishing them together spends the slot once.

**Verify competition entries survived the migration.** `add-explicit`
task 12.3 asked for a backfill run against a production copy before deploy. The
migration has since run on production for real, so the check becomes a
post-hoc one: confirm every pre-existing competition/project pair still holds a
`CompetitionEntry` row with a sensible `entered_via`. For reference, the dev
run produced 22 competitions and 111 entries, all `backfill`/`monthly`.

Note that `make seed-prod-copy` (`scripts/seed_prod_copy.py`) is not a database
copy — it mirrors live data through the public API at `api.naglasupan.is` and
carries none of the entry history. It cannot answer this question.

## Recorded

**Articles per house channel on production**, `merge-product-updates` task 6.1,
run 2026-08-19 via `house_channel_counts.py` (read-only; it lives in
[the archived change](../openspec/changes/archive/2026-08-19-merge-product-updates-into-updates/house_channel_counts.py)):

```
house project: naglasupan (Naglasúpan)
  'Competition Winners': articles=0 followers=90
  'Updates': articles=2 followers=89
  follows=92 of which empty=2
```

Two channels and no `Product Updates`, so `follows/0006` did what it said. The
unsubscribe event this change knowingly caused reaches at most **3 people** —
92 house follows against 89 on `Updates` — and **2** of them are now subscribed
to no house channel at all. That is the original platform-updates opt-out being
honoured, which was the point; it is worth knowing it is two people and not two
hundred. `Updates` carries 2 articles, so the surviving channel is live.

What this cannot confirm is the design's Migration Plan step 3 in full: the
follower count was supposed to match the pre-migration `Product Updates` count,
and that number no longer exists (see below). 89 stands on its own.

## Dead, deliberately

`merge-product-updates` task 6.2 — record pre-migration follower counts for
`Updates` and `Product Updates`. `follows/0006` ran on 2026-08-13; the counts it
would have compared against no longer exist outside a backup. The design's
verification step (its Migration Plan, step 3) is unrunnable for the same
reason. Not worth restoring a backup for.

## Deferred code, not tasks

Three things the article work chose not to build. They live in
[`openspec/changes/archive/2026-08-07-add-article-authoring/`](../openspec/changes/archive/2026-08-07-add-article-authoring/tasks.md)
— listed here only so they are findable:

- **Mixed digest email** (tasks 5.4 / 5.5). A recipient with both a comment and
  an article pending gets two emails. The immediate single-article send works;
  the combined template was never written.
- **Channel management UI** (§13). Every project auto-creates one `Updates`
  channel, so the editor's channel dropdown has a single option everywhere. The
  CRUD backend ships and is tested; only the UI is held back.
- **No signal for `article_trust = False` authors** (that change's
  `design.md:237`). Their article silently never reaches the feed and nothing
  tells them why.

## Content backfill was never started

Separate from all of the above:
[`docs/superpowers/specs/2026-05-13-articles-following-news-design.md`](superpowers/specs/2026-05-13-articles-following-news-design.md)
Phase 4 puts historical Naglasúpan output — old product updates, competition
results that went out by email — onto the platform as backdated articles, so the
feed is not empty above the launch date. Content op, not engineering: there is
no management command. `POST /articles/{id}/publish` takes `published_at`
(`api/routers/articles.py:247`) and backdating suppresses notification fan-out,
so the mechanism exists and someone has to write the copy and drive it.
