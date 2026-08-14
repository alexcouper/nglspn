## 1. Feed event storage

- [x] 1.1 Add the feed event model: `occurred_at`, event kind, references to the
      project / competition / article / discussion it concerns, superseded-by
      reference, retired flag, pinned flag
- [x] 1.2 Index on `occurred_at` descending; confirm the rendering query is a
      single query with no N+1 across the referenced entities
- [x] 1.3 Write the migration and verify with
      `uv run python manage.py makemigrations --check --dry-run`
- [x] 1.4 Add a `services/feed/` handler + repo pair following the existing
      `HANDLERS`/`REPO` layering; no ORM access from routers

## 1a. Competition winner timestamp

- [x] 1a.1 Add nullable `winner_announced_at` to Competition; set it in `save()`
      the first time a winner is assigned, leave it on re-assignment, clear it
      when the winner is cleared
- [x] 1a.2 Data migration backfilling it from `voting_end_date`, falling back to
      `submission_deadline`, only for competitions that have a winner
- [x] 1a.3 Tests for first assignment, re-assignment, clear-then-reassign, and
      the migration's two backfill paths

## 2. Appending events

- [x] 2.1 Append on article publish, at the article's `published_at`, including
      backdated publishes
- [x] 2.2 Append on project publish
- [x] 2.3 Append on community tipoff
- [x] 2.4 Append on competition opens / closes / winners announced
- [x] 2.5 Assert no append on article edit or delete, on discussion create, or on
      discussion reply
- [x] 2.6 Tests for each source, including the backdated-publish position case

## 3. Article ↔ event link and superseding

- [x] 3.1 Add the optional event reference to Article and its migration
- [x] 3.2 Retire the referenced event when a linked article publishes; render one
      entry carrying the event's flag and the article's headline
- [x] 3.3 Enforce one-shot superseding — a second article referencing an already
      superseded event becomes its own entry
- [x] 3.4 Restore the bare event to rendering when a superseding article is
      deleted
- [x] 3.5 Offer the inferable event as the publish dialog's default where the
      article is on the house project's Competition Winners channel
- [x] 3.6 Tests: supersede, one-shot, unlinked duplicate renders both, delete
      restores

## 4. Read API

- [x] 4.1 Cursor-paginated feed endpoint ordered by `occurred_at` descending,
      excluding retired events
- [x] 4.2 Resolve each entry to its render shape — flag, title, link target, and
      where an article is attached its listing image, crop and summary
- [x] 4.3 Expose the lead separately from the list, gated on the configurable
      freshness window (default 7 days) and on an admin pin
- [x] 4.4 Tests: paging serves each entry exactly once; a stale newest article
      produces no lead; a bare newest event produces no lead; a pin overrides
- [x] 4.5 Regenerate and commit the contract:
      `cd src/django-backend && make extract-openapi`

## 5. Admin surfaces

- [x] 5.1 Django admin action to promote a discussion thread into the feed, and
      to retire a promoted entry
- [x] 5.2 Django admin action to pin and unpin an entry as the lead
- [x] 5.3 Django admin affordance to set an article's event reference after
      publish, retiring the bare event

## 6. Shared tab bar

- [x] 6.1 Extract the tab bar from `src/web-ui/src/app/projects/ProjectsPage.tsx`
      into shared chrome rendered by both `/latest` and `/projects`
- [x] 6.2 Add "Latest" as the first tab, ahead of "Discover"
- [x] 6.3 Confirm the existing category-view and discover-view behaviour is
      unchanged, including the sticky offset below the nav

## 7. Latest view

- [x] 7.1 Add the `/latest` route; leave `/` redirecting to `/projects`
- [x] 7.2 Feed row component covering all three entry states from one shape;
      reuse `ArticleCard`'s treatment for the article-carrying states rather than
      duplicating it
- [x] 7.3 Full-width lead card, rendered only when the API supplies a lead
- [x] 7.4 Week grouping headers
- [x] 7.5 Load-more paging against the cursor endpoint
- [x] 7.6 Empty state: short line plus a link to Discover
- [x] 7.7 Single-column layout at mobile widths, lead full width
- [x] 7.8 Component tests for the three entry states, the imageless article case,
      and lead present / absent

## 8. Backfill

- [x] 8.1 Management command seeding events from existing published projects,
      tipoffs and competitions at their original timestamps, back to the earliest
      record with no cut-off. Articles are out of scope — they arrive through the
      publish path
- [x] 8.2 Make it idempotent: a re-run appends only what earlier runs missed and
      duplicates nothing. Test the run-twice and run-after-new-records cases
- [x] 8.3 Assert the command fires no in-app notification and no email
- [ ] 8.4 Launch sequencing: ship the feed, run the backfill, then publish the
      pending drafts — the house announcement first — a few days apart so each
      takes a turn as the lead

## 9. Verification

- [x] 9.1 Backend: `make lint`, `make extra-tests`, `make test`
- [x] 9.2 Web UI: `make lint`, `make test`, `make build-app`, `make extra-tests`
- [x] 9.3 Drive `/latest` in a browser against seeded data: lead present, lead
      absent, superseded pair shows once, paging, mobile width
