# Design: add explicit competition entry

## Context

See [`proposal.md`](proposal.md) for the motivation. In short: competition entry
is an unannounced side effect of publishing, and publishing between rounds
strands a project permanently.

The current mechanism, in full, is these ten lines in
`services/project/django_impl/handler.py:215-224`:

```python
if not project.is_community_tipoff:
    open_competition = (
        Competition.objects.filter(status=CompetitionStatus.ACCEPTING_APPLICATIONS)
        .order_by("-start_date").first()
    )
    if open_competition is not None:
        open_competition.projects.add(project)
```

That is the only write to `Competition.projects` outside the admin and the seed
scripts. Everything else — the competition page's project list, reviewer
assignment, `RankedProject` — reads the relation.

Four existing facts shape the design:

- **`Competition.projects` is a plain M2M** (`apps/projects/models.py:393`) with
  `related_name="competitions"`. Readers across `api/routers/competitions.py`,
  `services/review/`, `scripts/seed_db.py` and the tests use both directions.
  The relation's *name* must survive this change even though its storage does
  not.
- **A competition has no type.** `Competition` (`apps/projects/models.py:377`)
  carries a name, a slug, dates, a prize and a status. Nothing distinguishes the
  recurring monthly round from a one-off, so nothing can scope a rule to one of
  them.
- **Round status is set by hand.** Nothing schedules the
  `ACCEPTING_APPLICATIONS → VOTING → CLOSED` transitions; an admin does. Gaps
  between rounds are the normal state, not an edge case, which is why the
  silent-loss bug is reachable at all. Nothing stops two rounds being open at
  once either.
- **Publish is one-way and one-shot.** `publish()` requires `status = DRAFT`
  (`handler.py:191`) and the spec forbids ever returning to `DRAFT`
  (`openspec/specs/project-draft-publish/spec.md:118`). So "retry the publish
  when a round opens" is not available as a fix; entry needs its own path.

## Goals / Non-Goals

**Goals:**

- A user always knows which rounds their project is in, which it was in, and
  which it could enter now.
- Entering is a decision, made explicitly, never a surprise.
- A project published while no round was open can enter the next one.
- A project that ran in one series can enter a different one.
- Entry carries an audit trail: when, how, and at whose hand.
- The eligibility rules exist in exactly one place, on the server.

**Non-Goals:**

- Re-entry into the same series. One entry per series, ever.
- A withdraw path. Admin only.
- Automating round status transitions.
- Changing who may enter: community tipoffs stay out, as they are today.
- Making a series a first-class object with its own page, prize or branding.

## Decisions

### A through-model, not a parallel table or a status field

`CompetitionEntry` becomes the `through` on the existing M2M rather than a
separate audit log alongside it:

```python
class EntrySource(models.TextChoices):
    MANUAL = "manual", "Entered by contributor"
    ADMIN = "admin", "Added by admin"
    BACKFILL = "backfill", "Backfilled"

class CompetitionEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name="entries")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="competition_entries")
    entered_at = models.DateTimeField(default=timezone.now)
    entered_via = models.CharField(max_length=20, choices=EntrySource.choices)
    entered_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = "competition_entries"
        unique_together = ("competition", "project")
```

A parallel audit table would let the M2M and the log disagree — one write path
succeeding while the other fails is the classic way audit trails start lying.
With a through-model there is only one row, so membership and its provenance
cannot diverge.

`related_name="competitions"` is preserved on the M2M, so every existing reader
is untouched. This is the point of using `through=` rather than replacing the
relation.

`entered_at` is `default=timezone.now`, not `auto_now_add`, specifically so the
backfill can write real historical timestamps instead of stamping every
pre-existing entry with the deploy time.

`entered_by` is nullable with `on_delete=SET_NULL`: backfilled and admin-added
rows have no user to point at, and deleting an account must not delete a round's
history.

There is no `publish` source because publishing no longer enters anything.

### Exclusivity is scoped by a series slug on the competition

```python
entry_series = models.SlugField(max_length=50, default="monthly", db_index=True)
```

The rule this exists to express is: *a project gets one shot at the monthly
round, but an occasional one-off is open to everybody, including projects that
already ran.* That needs competitions to be groupable, and today they are not.

A slug on `Competition` rather than a `CompetitionSeries` model. A model would
buy a name, a description and somewhere to hang future per-series rules; none of
those are wanted yet, and it costs a table, an admin, a backfill and an API
surface to describe what is currently one recurring series plus the occasional
one-off. A slug means starting a new series is typing a new value in the admin.

Rejected alternative: a `TextChoices` `kind` field (`monthly`, `special`). Two
unrelated one-offs both tagged `special` would wrongly exclude each other, and
every new series would be a code change plus a migration.

**The default is `"monthly"`, not blank.** The failure mode matters more than
the tidiness: an admin who forgets the field on a new round gets exclusivity
applied, which is at worst a project that cannot enter and complains. Defaulting
to blank would make the same slip silently readmit every past entrant to the
monthly round, which is unrecoverable once voting starts. Existing rows all take
the default in the migration, which is what they are.

### The one-entry-per-series rule lives in the handler, not the database

`unique_together` stops the same project entering the same round twice — that is
a data-integrity rule and belongs in the schema. "A project may only ever be in
one competition per series" is a product rule that will want exceptions (an
admin re-running a round, a project that was entered by mistake), so it is a
handler check that returns `400`. Encoding it as a constraint would make every
exception a migration, and it is not expressible as one anyway: the constraint
would have to span `competition_entries` and `competitions`.

### Standing is a list of entries and a list of opportunities

A project can now be in several competitions and eligible for several more, so
the four-state answer (`entered` / `eligible` / `no_open_round` /
`not_eligible`) no longer has anything to attach itself to. It is replaced by an
evaluation of the project against *every* open competition:

```python
@dataclass(frozen=True)
class ProjectEntry:
    competition: Competition
    entered_at: datetime
    entered_via: str

@dataclass(frozen=True)
class CompetitionOpportunity:
    competition: Competition
    eligible: bool
    reason: str | None                  # set when eligible is False
    blocking_entry: Competition | None  # set when reason is already_in_series

@dataclass(frozen=True)
class CompetitionStanding:
    entries: list[ProjectEntry]              # newest first
    opportunities: list[CompetitionOpportunity]
```

Eligibility for one open competition `C`, first match wins:

1. the project is a community tipoff → `community_project`
2. the project's `status` is `REJECTED` or `ICE_BOX` → `project_status`
3. an entry exists in a competition whose `entry_series` equals `C.entry_series`
   → `already_in_series`, naming that competition
4. otherwise → eligible

`opportunities` holds one of these per competition with
`status = ACCEPTING_APPLICATIONS`. "No round is open" is an empty list, not a
state — a single `blocked_reason` field would have to mean "no rounds exist",
"you're already in this series" and "tipoffs can't enter" at once, and the UI
cannot tell those apart to render them.

`reason` is reported per opportunity even where it is project-wide, so the API
stays uniform; the UI collapses a reason repeated across every row into one line
rather than the server special-casing it.

The same function backs the `competition_standing` field on `ProjectResponse`
and the validation inside the entry endpoint, so the controls and the endpoint
can never disagree about who may enter.

**A `DRAFT` project gets opportunities like any other.** "May this project enter
this round" is the same question whatever its status, and the post-publish
dialog needs the answer computed before the project is published. The endpoint
separately rejects a `DRAFT` project with `400`, because entering without
publishing is not a thing.

The alternative — the client fetching the open competitions and working the
rules out itself — was rejected: it duplicates the rules in TypeScript, and the
drift surfaces as a button that 400s.

### One open-round query per request, not per project

`/api/my-projects` returns a list, and a naive resolver would evaluate the open
rounds once per project. `DjangoProjectQuery.with_competition_standing(qs)`
prefetches `competition_entries__competition`, resolves the open competitions
once, and stamps `_competition_standing` on each instance;
`ProjectResponse.resolve_competition_standing` reads the stamped value and falls
back to computing it for a single un-stamped instance. Total cost for a list:
two queries beyond what is already run.

### `competition_standing` is null on public project responses

`ProjectResponse` is shared between `/api/my-projects/*` and the public
`/api/projects/{identifier}`. Somebody else's entry opportunities are
meaningless, and computing them would add queries to every public page. The
field is populated only on the `my-projects` routes and is `null` elsewhere,
following `is_followed`, which is already route-dependent in exactly this way.

The public page keeps `won_competitions`, which is unrelated and unchanged.

### Publishing publishes; entry is always a separate request

The auto-entry block is deleted rather than made optional. An
`enter_competition` flag on the publish body was considered and dropped: with
several rounds potentially open, a boolean cannot say *which*, and a list of
competition ids on a publish request makes publishing carry a second, unrelated
transaction that can half-fail. Publish returns the project; the client then
calls the entry endpoint, once, for the round the user picked.

This **is** a behaviour change for anything calling `POST /publish` directly —
it used to enter the open round and now enters nothing. The only in-repo caller
is the web UI, which is updated in the same change; the endpoint's request and
response shapes are unchanged.

The entry endpoint therefore takes a required `competition_id`. Inferring "the
newest open round" server-side would silently pick for the user exactly where
the old bug lived.

### The publish dialog moves after the publish, not before

Pressing **Publish** calls the API, which may return `400` with `missing` — at
which point the existing `PublishDialog` takes over, unchanged. On `200`, if the
now-published project has eligible opportunities, `EnterCompetitionDialog` opens
listing them with their deadlines; the contributor enters one or dismisses.

Asking beforehand would mean naming the rounds the project *would* be able to
enter if it published successfully, which is a promise the precondition check
can break a second later. Asking afterwards means the offer is real. Dismissing
costs nothing: the same rounds are on the project page with the same controls.

### One component owns competitions on the project page

`ProjectCompetitions` renders both halves of the standing as rows in one
section — entered rounds with their dates, status and the existing
`won_competitions` marker; then open rounds, each with an **Enter** control or,
where `eligible` is false, the reason inline. Two open rounds is two rows, which
reads as a list rather than as competing calls to action.

Where a reason is project-wide (`community_project`, `project_status`) the
component states it once instead of once per row. Where there are no entries and
no opportunities it renders a single line — no rounds are open, the project can
enter the next one — rather than vanishing, so the page never goes quiet about
competitions.

`/my-projects` cards get a compressed read-only form of the same data and no
controls; entering from a list of cards would need the round picked per card,
which is the project page's job.

### `/submit` becomes enter-or-create

The eligible-project chooser sits above the existing URL form rather than on the
competition page. The competition CTA links to `/submit?competition=<id>`, which
heads the chooser with that round and filters to projects eligible for it; with
no parameter it lists every project with any eligible opportunity. One page owns
submission, and the competition page keeps a single button.

No new endpoint: `GET /api/my-projects` already returns `competition_standing`,
so the chooser filters what it already has. An empty list renders nothing and
`/submit` looks exactly as it does today.

### Admin loses the dual-list picker

Django's `admin.E013` forbids `filter_horizontal` and form `fields` on a M2M
with a `through` model, so `CompetitionAdmin`'s `filter_horizontal =
("projects",)` (`apps/projects/admin.py:657`) and its **Projects** fieldset must
go or `manage.py check` fails. A `CompetitionEntryInline` with
`autocomplete_fields = ("project",)` replaces them, defaulting `entered_via` to
`admin` and stamping `entered_by` from `request.user`.

Honestly a downgrade in ergonomics: adding twenty projects to a round becomes
twenty autocomplete rows rather than a multi-select. Given rounds are assembled
by users entering themselves, and admin additions are the exception, the audit
trail is worth more than the picker.

## Risks / Trade-offs

- ~~**The backlog floods the next round.**~~ Answered: production has no
  published project that is not already in a competition, so there is no
  backlog to let in. The rule that a project published between rounds can enter
  the next one is preventative rather than remedial. The corollary is worth
  stating plainly: every project in production already holds a `monthly` entry,
  so none of them can enter another `monthly` round. The next monthly round
  starts empty and fills with newly published projects, exactly as it does
  today. A one-off series is how an existing project gets a second run.
- **Publishing no longer enters, and nobody reads release notes.** A user who
  publishes and dismisses the dialog is not in the round, where before they
  would have been. → The project page states the standing permanently and offers
  the control, so the path back is one click and always visible. This is the
  price of the feature: the silent side effect is what the change exists to
  remove.
- **`entry_series` is free text and typos are silent.** `monthy` is a new series
  that excludes nothing. → The default covers the common case, and the admin
  form shows existing values; a typo is visible on the competition page's own
  admin row. Not worth a lookup table yet.
- **The M2M `through` swap is a three-step migration over live data.** A partial
  run leaves entries in one table and not the other. → The data migration is
  reversible and idempotent (`get_or_create` keyed on the unique pair), and the
  swap is state-only from Django's perspective — the rows already live in
  `competition_entries` by then. Verify the row count matches before and after
  on a production copy (`scripts/seed_prod_copy.py`).
- **Two users entering the same project concurrently**, or a user entering while
  an admin does. → `unique_together` makes the loser's insert fail; the handler
  catches `IntegrityError` and returns `409`, which the UI treats as success and
  re-fetches.
- **A round closes between the page render and the button press.** → The handler
  re-evaluates opportunities, so a stale control returns `400` rather than
  entering a closed round. The UI shows the error and re-fetches.
- **`entered_via` will be wrong for anything written outside the handler** —
  a `competition.projects.add(project)` elsewhere would need a default. → The
  seed scripts are updated to pass a source explicitly; there is no other
  writer.

## Migration Plan

1. `0047_competition_entry_series` — add `entry_series` with
   `default="monthly"`, which stamps every existing competition.
2. `0048_competitionentry` — create the model and its table.
3. `0049_backfill_competition_entries` — copy every row from
   `competitions_projects` with `entered_via = "backfill"`,
   `entered_at = project.published_at or competition.start_date`,
   `entered_by = None`. Reversible: delete the backfilled rows.
4. `0050_competition_projects_through` — point the M2M at `CompetitionEntry`.

Deploy is a single release; all four run in one `migrate`. Rollback before the
next round opens is `migrate 0046`, which restores the plain M2M — the backfill
put nothing in `competition_entries` that is not also in the original table
until step 4 drops it, so nothing is lost. After entries have been created
through the new endpoint, rollback means data loss and should not be attempted;
roll forward instead.

## Open Questions

None. The one that was open — how many published, un-entered projects exist —
is answered: none. Production has no project outside a competition, so nothing
becomes newly eligible for a `monthly` round on deploy. The query, for whoever
wants to confirm it against a production copy before migrating:

```python
Project.objects.filter(
    published_at__isnull=False,
    is_community_tipoff=False,
    competition_entries__isnull=True,
).exclude(status__in=["draft", "rejected", "ice_box"]).count()
```
