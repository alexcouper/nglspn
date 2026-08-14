# Design: clarify pending competition entries

## Context

See [`proposal.md`](proposal.md). All three findings come from one walk through
the flow built by
[`refine-competition-entry-surfaces`](../refine-competition-entry-surfaces/design.md).
Nothing about entry rules or the endpoint changes; this is about a project that
is entered and waiting, and the fact that three surfaces describe that state
badly or twice.

The facts underneath:

- **Publishing produces `PENDING`, not live.** `publish()` sets
  `ProjectStatus.PENDING` (`handler.py:205`) and an admin moves it to `APPROVED`
  by hand. There is no scheduler.
- **Entry is independent of approval.** A `PENDING` project can enter and hold a
  `CompetitionEntry`; nothing re-checks status later. Approval changes only
  whether the project is *visible* in the round.
- **The round's public list filters to `APPROVED`**
  (`api/schemas/competition.py:71`). So "entered" and "shown in the round" are
  different sets, and the gap between them is exactly the review queue.
- **`GET /api/my/projects` already carries what the dialog needs**: every
  project's `status` and its `competition_standing.entries`. No new endpoint.

## Goals / Non-Goals

**Goals:**

- A contributor is never told their project is published when it is queued.
- "You can't enter" is never said to someone who is already in.
- A round appears once in a project's competitions section.

**Non-Goals:**

- Changing who may enter, or when.
- Making unapproved projects visible to anybody but their owner.
- Automating review.

## Decisions

### An already-entered round stops being an opportunity

```python
entered_ids = {entry.competition_id for entry in entries}
opportunities=[
    _opportunity(project, competition, blocking_by_series)
    for competition in open_competitions
    if competition.id not in entered_ids
]
```

The duplicate exists because `opportunities` was defined as *every* open
competition, and `already_in_series` then matched the project's own entry — so a
round it had entered came back as a round it could not enter, naming itself as
the blocker. The nonsense is in the question, not the answer: "may this project
enter this round" is not a question worth asking about a round it is in.

Server-side rather than filtering in `ProjectCompetitions`, for the reason the
original design gives for putting eligibility on the server: the rule then holds
for every consumer, and the redundant rows never travel. The narrowing is small
and total — `entries` already reports those rounds, with more detail than an
opportunity carries.

This also removes the only case where `blocking_entry` could name the same
competition as the opportunity, which was never meaningful.

**Consequence worth stating**: `opportunities` is no longer "the open rounds".
It is "the open rounds this project is not in", which is what every caller
actually wanted. The Settings heading changes to match — **Other rounds open
now** — and the empty line has to distinguish two cases it previously could not:

| entries | opportunities | line |
|---|---|---|
| any | none | "No other round is open right now." |
| none | none | "No round is currently open. This project can enter the next one." |

Without that split, a project sitting in all three open rounds would be told no
round is open.

### The chooser answers "where do I stand", not just "what can I enter"

The dialog gets a section above the choice list listing the user's projects
already in *this* round, each labelled by what the contributor is waiting on:

- `APPROVED` → **Live in the round**
- `PENDING` → **Awaiting review**
- anything else → the project's status, plainly

Computed from data already fetched: a project is in this round when its
`competition_standing.entries` contains this competition's id.

Only this round, not the whole series. A project blocked because it is in
*February's* round is a different sentence, and the reviewer's call was to keep
the dialog to the round in front of the user. The project page carries the
series story already, with the blocking round named.

The closing line then depends on what is actually true, rather than always
claiming a lock-out:

- something to enter → the choice list and its footer, as now
- nothing to enter but something already in → "Nothing else of yours can enter
  this round."
- nothing at all, but the user has projects → the existing "None of your
  projects can enter this round…"
- no projects → the existing "You haven't added a project yet."

Rejected: computing this server-side as a per-competition "my projects" summary.
It would be a new endpoint returning a view of data the client already holds,
and the grouping is presentation.

### The publish dialog states the outcome, not the aspiration

*"That's it sent. Enter it in a competition?"* over *"It goes live once we've
reviewed it. Entering now is fine — it joins the round on approval."*

Two things have to land in two lines: the project is not live yet, and entering
now is not premature. The second matters more than it looks — a contributor told
"we'll review this" reasonably assumes competition entry waits for the verdict,
and the whole point of the dialog is that it does not.

The rest of the dialog — the rounds, the radios, the footer, the trailing note
about entering later from the project page — is unchanged.

## Risks / Trade-offs

- **`opportunities` changes meaning, and a caller could be counting on the old
  one.** → The only consumers are `ProjectCompetitions` and `EnterProjectDialog`,
  both in this repo and both updated here. The chooser filters on `eligible`, so
  dropping already-entered rounds cannot change what it lists.
- **The chooser now renders projects the user cannot act on.** → That is the
  point of the finding; the previous silence read as refusal. It stays a list of
  names and states, with no controls, above the part that does act.
- **"Awaiting review" sets an expectation about timing that nothing keeps.**
  Review is manual and unscheduled. → The line promises order, not speed, and it
  is a truer description than the current implication that the project is out.
- **The round's project count still disagrees with its list**, and this change
  makes pending entries more visible without fixing that. → Filed deliberately;
  the count is a public-page concern and the reviewer chose to take it
  separately.

## Open Questions

None.
