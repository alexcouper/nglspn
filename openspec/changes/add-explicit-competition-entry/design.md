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

Three existing facts shape the design:

- **`Competition.projects` is a plain M2M** (`apps/projects/models.py:393`) with
  `related_name="competitions"`. Readers across `api/routers/competitions.py`,
  `services/review/`, `scripts/seed_db.py` and the tests use both directions.
  The relation's *name* must survive this change even though its storage does
  not.
- **Round status is set by hand.** Nothing schedules the
  `ACCEPTING_APPLICATIONS → VOTING → CLOSED` transitions; an admin does. Gaps
  between rounds are the normal state, not an edge case, which is why the
  silent-loss bug is reachable at all.
- **Publish is one-way and one-shot.** `publish()` requires `status = DRAFT`
  (`handler.py:191`) and the spec forbids ever returning to `DRAFT`
  (`openspec/specs/project-draft-publish/spec.md:118`). So "retry the publish
  when a round opens" is not available as a fix; entry needs its own path.

## Goals / Non-Goals

**Goals:**

- A user always knows whether their project is in a round, and which.
- Entering is a decision, made at publish or later, never a surprise.
- A project published while no round was open can enter the next one.
- Entry carries an audit trail: when, how, and at whose hand.
- The eligibility rules exist in exactly one place, on the server.

**Non-Goals:**

- Re-entry into a second round. One round per project, ever.
- A withdraw path. Admin only.
- Automating round status transitions.
- Changing who may enter: community tipoffs stay out, as they are today.

## Decisions

### A through-model, not a parallel table or a status field

`CompetitionEntry` becomes the `through` on the existing M2M rather than a
separate audit log alongside it:

```python
class EntrySource(models.TextChoices):
    PUBLISH = "publish", "At publish"
    MANUAL = "manual", "Entered later"
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

### The "one round ever" rule lives in the handler, not the database

`unique_together` stops the same project entering the same round twice — that is
a data-integrity rule and belongs in the schema. "A project may only ever be in
one round" is a product rule that will want exceptions (an admin re-running a
round, a project that was entered by mistake), so it is a handler check that
returns `400`. Encoding it as a constraint would make every exception a
migration.

### Entry state is computed on the server and rendered blindly by the client

The four eligibility inputs — is it published, is it a community tipoff, is it
already in a round, is a round open — are evaluated once, in
`DjangoProjectQuery.competition_entry_state()`, returning:

```python
@dataclass(frozen=True)
class CompetitionEntryState:
    state: Literal["entered", "eligible", "no_open_round", "not_eligible"]
    competition: Competition | None
    entered_at: datetime | None
    reason: str | None          # populated for not_eligible
```

Rules, first match wins:

1. a `CompetitionEntry` exists → `entered` (that competition, its `entered_at`)
2. community tipoff → `not_eligible`, reason `community_project`
3. `status` in `REJECTED`, `ICE_BOX` → `not_eligible`, reason `project_status`
4. no round with `status = ACCEPTING_APPLICATIONS` → `no_open_round`
5. otherwise → `eligible`, carrying the open round

The same function backs the `competition_entry` field on `ProjectResponse` and
the validation inside the entry endpoint, so the button and the endpoint can
never disagree about who may enter.

**A `DRAFT` project is `eligible`.** It enters via publish rather than the
button, but "may this project enter the open round" is the same question and
deserves the same answer. The client already has `project.status` and branches
on it to choose which affordance to show — a publish dialog for a draft, an
Enter button for a published project. The alternative, a fifth state like
`eligible_on_publish`, encodes a UI distinction in the domain model for no gain.

The endpoint additionally rejects a `DRAFT` project with `400`, because entering
without publishing is not a thing.

The alternative — the client fetching the open competition and working the rules
out itself — was rejected: it duplicates four rules in TypeScript, and the drift
surfaces as a button that 400s.

### One open-round query per request, not per project

`/api/my-projects` returns a list, and a naive resolver would look up the open
round once per project. `DjangoProjectQuery.with_competition_entry_state(qs)`
prefetches `competition_entries__competition`, resolves the open round once, and
stamps `_competition_entry_state` on each instance;
`ProjectResponse.resolve_competition_entry` reads the stamped value and falls
back to computing it for a single un-stamped instance. Total cost for a list:
two queries beyond what is already run.

### `competition_entry` is null on public project responses

`ProjectResponse` is shared between `/api/my-projects/*` and the public
`/api/projects/{identifier}`. `eligible` or `no_open_round` on somebody else's
project is meaningless, and computing it would add queries to every public page.
The field is populated only on the `my-projects` routes and is `null` elsewhere,
following `is_followed`, which is already route-dependent in exactly this way.

### The publish request body is optional

`POST /api/my-projects/{id}/publish` takes `{ "enter_competition": bool }`
defaulting to `true`. Omitting the body reproduces today's behaviour exactly, so
the endpoint stays backwards compatible and the change to
`src/lib/api/my-projects.ts` is additive.

Declining entry at publish is not permanent — it leaves the project `eligible`,
and the Enter button appears on its page. There is no "never enter" flag; the
user who ticks nothing today can change their mind next week.

### The publish dialog confirms first and validates second

Pressing **Publish** opens the confirmation dialog, which names the round and
deadline (or states that none is open) and offers the entry checkbox. Confirming
calls the API, which may still return `400` with `missing` — at which point the
existing `PublishDialog` takes over, unchanged.

This means a user can occasionally confirm and then be told the project is not
ready. The alternative, a `publish-preview` endpoint returning missing fields
and the open round up front, is a nicer flow and a whole extra endpoint; and
re-implementing `_publish_preconditions_missing` in TypeScript to pre-check is
the drift trap again. The occasional two-step is the cheaper wrong.

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

- **The backlog floods the next round.** Every previously-published,
  un-entered project becomes eligible at once, and the next round could be much
  larger than the last. → Accepted deliberately: those users are the ones the
  bug stranded. Mitigation if it bites: the round's status is admin-controlled,
  so entry can be closed early. Worth counting the orphans before deploying, and
  worth telling reviewers the round may be bigger than usual.
- **The M2M `through` swap is a three-step migration over live data.** A partial
  run leaves entries in one table and not the other. → The data migration is
  reversible and idempotent (`get_or_create` keyed on the unique pair), and the
  swap in step 3 is state-only from Django's perspective — the rows already
  live in `competition_entries` by then. Verify the row count matches before and
  after on a production copy (`scripts/seed_prod_copy.py`).
- **Two users entering the same project concurrently**, or a user entering while
  an admin does. → `unique_together` makes the loser's insert fail; the handler
  catches `IntegrityError` and returns `409`, which the UI treats as success and
  re-fetches.
- **A round closes between the page render and the button press.** → The handler
  re-checks the round's status, so a stale `eligible` returns `400` rather than
  entering a closed round. The UI shows the error and re-fetches.
- **`entered_via` will be wrong for anything written outside the handler** —
  a `competition.projects.add(project)` elsewhere would need a default. → The
  seed scripts are updated to pass a source explicitly; there is no other
  writer.

## Migration Plan

1. `0047_competitionentry` — create the model and its table.
2. `0048_backfill_competition_entries` — copy every row from
   `projects_competition_projects` with `entered_via = "backfill"`,
   `entered_at = project.published_at or competition.start_date`,
   `entered_by = None`. Reversible: delete the backfilled rows.
3. `0049_competition_projects_through` — point the M2M at `CompetitionEntry`.

Deploy is a single release; steps 1-3 run in one `migrate`. Rollback before the
next round opens is `migrate 0046`, which restores the plain M2M — the backfill
put nothing in `competition_entries` that is not also in the original table
until step 3 drops it, so nothing is lost. After entries have been created
through the new endpoint, rollback means data loss and should not be attempted;
roll forward instead.

## Open Questions

None blocking. One worth answering with data before deploy: how many published,
un-entered, non-tipoff projects exist? It sets expectations for the size of the
next round and is a one-line query.
