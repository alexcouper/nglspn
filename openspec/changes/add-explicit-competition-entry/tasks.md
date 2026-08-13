# Tasks: add explicit competition entry

## 1. Measure the backlog before committing to it

- [ ] 1.1 Against a production copy, count published, non-tipoff projects with no row in `projects_competition_projects`: this is the set that becomes eligible on deploy. Record the number in `design.md`'s Open Questions.
- [ ] 1.2 If the number is large enough to change how the next round is run, say so before implementing — the fix is unchanged, but the round needs warning.

## 2. Model and migrations

- [ ] 2.1 Add `EntrySource` (`publish`, `manual`, `admin`, `backfill`) and `CompetitionEntry` to `src/django-backend/apps/projects/models.py`, with `db_table = "competition_entries"`, `unique_together = ("competition", "project")`, `entered_at = DateTimeField(default=timezone.now)` and `entered_by` nullable with `on_delete=SET_NULL`.
- [ ] 2.2 Generate migration `0047_competitionentry` creating the model only — leave `Competition.projects` alone at this step.
- [ ] 2.3 Write data migration `0048_backfill_competition_entries` copying every row from the auto-created `projects_competition_projects` table using `get_or_create` on `(competition, project)`, with `entered_via = "backfill"`, `entered_at = project.published_at or competition.start_date`, `entered_by = None`. Give it a reverse that deletes only `entered_via = "backfill"` rows. Use the historical model from `apps.registry`, not the imported one.
- [ ] 2.4 Change `Competition.projects` to `ManyToManyField(Project, through="CompetitionEntry", related_name="competitions", blank=True)` and generate `0049_competition_projects_through`.
- [ ] 2.5 Run `uv run python manage.py makemigrations --check --dry-run` and confirm it reports nothing outstanding.
- [ ] 2.6 Add a migration test asserting the backfill preserves row count and maps timestamps as specified, including a project with `published_at = None` falling back to the competition's `start_date`.

## 3. Admin

- [ ] 3.1 Remove `filter_horizontal = ("projects",)` (`apps/projects/admin.py:657`) and the `"Projects"` fieldset — Django's `admin.E013` rejects both on a `through` M2M.
- [ ] 3.2 Add `CompetitionEntryInline` (tabular) with `autocomplete_fields = ("project",)` and `readonly_fields = ("entered_at", "entered_via", "entered_by")` for existing rows; register it on `CompetitionAdmin` alongside `CompetitionReviewerInline`.
- [ ] 3.3 Stamp `entered_via = ADMIN` and `entered_by = request.user` on inline rows created through the admin.
- [ ] 3.4 Run `uv run python manage.py check` and confirm no `admin.E013` or related system-check errors.

## 4. Eligibility, in one place

- [ ] 4.1 Add `CompetitionEntryState` (frozen dataclass: `state`, `competition`, `entered_at`, `reason`) to `services/project/query_interface.py`.
- [ ] 4.2 Implement `competition_entry_state(project)` in `services/project/django_impl/query.py` applying the five ordered rules from `design.md`; a `DRAFT` project is `eligible`.
- [ ] 4.3 Implement `with_competition_entry_state(qs)` in the same module: prefetch `competition_entries__competition`, resolve the open round once, stamp `_competition_entry_state` on each instance.
- [ ] 4.4 Unit-test each rule in `services/project/django_impl/test_query.py`, including the precedence cases: entered-in-a-closed-round beats an open round; tipoff beats an open round; newest `start_date` wins among several open rounds.

## 5. Publish takes a choice

- [ ] 5.1 Change `ProjectHandlerInterface.publish` and `DjangoProjectHandler.publish` to accept `enter_competition: bool = True`.
- [ ] 5.2 Replace the `open_competition.projects.add(project)` call (`services/project/django_impl/handler.py:224`) with a `CompetitionEntry` create carrying `entered_via = PUBLISH` and `entered_by = owner_id`, gated on `enter_competition` as well as the existing tipoff and open-round conditions.
- [ ] 5.3 Add `PublishRequest` (`enter_competition: bool = True`) to `api/schemas/project.py` and accept it as an optional body on `POST /api/my-projects/{id}/publish`, keeping a bodyless request working.
- [ ] 5.4 Extend `api/routers/test_my_projects.py`: publish with no body enters the open round; `{"enter_competition": false}` publishes without entering and leaves the project `eligible`; `true` with no open round publishes and leaves it `no_open_round`; a community-owned project never enters whatever the flag says; a `400` on missing fields creates no entry.

## 6. The entry endpoint

- [ ] 6.1 Add `enter_competition(project_id, owner_id)` to the project handler interface and its Django implementation: re-evaluate state, reject anything but `eligible`, reject `status = DRAFT` separately, create the entry with `entered_via = MANUAL` and `entered_by`, catch `IntegrityError` from the unique constraint and raise a distinct error for it.
- [ ] 6.2 Add `POST /api/my-projects/{project_id}/competition-entry` to `api/routers/my_projects.py` returning `200 ProjectResponse`, `400` (not eligible / draft), `404` (no `full_edit`), `409` (concurrent entry).
- [ ] 6.3 Cover every scenario in `specs/competition-entry/spec.md` under "A published project can enter an open round" in `api/routers/test_my_projects.py`, including a project published between rounds entering the next one.

## 7. Entry state on the API

- [ ] 7.1 Add `CompetitionEntryStateResponse` and a competition summary (`id`, `name`, `slug`, `status`, `submission_deadline`) to `api/schemas/project.py`.
- [ ] 7.2 Add `competition_entry: CompetitionEntryStateResponse | None = None` to `ProjectResponse` with a resolver reading the stamped `_competition_entry_state`, falling back to computing it for a single instance.
- [ ] 7.3 Apply `with_competition_entry_state` in the `/api/my-projects` list and detail paths only; leave the public project queries alone so `competition_entry` is null there.
- [ ] 7.4 Add a query-count test over `GET /api/my-projects` with several projects, asserting the count does not grow with the number of projects.
- [ ] 7.5 Assert `competition_entry` is null on `GET /api/projects/{identifier}`.
- [ ] 7.6 Run `make extract-openapi` in `src/django-backend/` and commit `src/web-ui/backend-openapi.json` — `make extra-tests` fails without it.

## 8. Frontend plumbing

- [ ] 8.1 Run `npm run generate-types` in `src/web-ui/` (do not commit `src/lib/api-types.ts`).
- [ ] 8.2 Add the optional publish body to `api.myProjects.publish` and a new `api.myProjects.enterCompetition(id)` in `src/lib/api/my-projects.ts`.

## 9. Frontend surfaces

- [ ] 9.1 Add `CompetitionEntryBadge` rendering the four states per `specs/competition-entry/spec.md`, with no eligibility logic of its own.
- [ ] 9.2 Add `PublishConfirmDialog`: names the round and its `submission_deadline` with an entry checkbox defaulting to checked; states plainly when no round is open; cancel leaves the project unpublished.
- [ ] 9.3 Wire it into `ProjectDetail.tsx` ahead of the publish call, keeping the existing `PublishDialog` for the `400 missing` response.
- [ ] 9.4 Render `CompetitionEntryBadge` on `/my-projects/[id]`, with the **Enter in \<round\>** control for a published `eligible` project; on success re-fetch, on failure show the error and re-fetch.
- [ ] 9.5 Render the badge on each card in `ProjectsList.tsx`.
- [ ] 9.6 Add an "already have a project?" section to `/submit` listing the user's `eligible` published projects, each linking to `/my-projects/<id>`; render nothing when the list is empty.
- [ ] 9.7 Change the competition CTA (`CompetitionReveal.tsx:122-140`) so an authenticated user with an eligible project sees a route to enter it alongside "Submit a Project"; anonymous and no-eligible-project users see today's CTA unchanged.
- [ ] 9.8 Vitest cover: badge in each of the four states; publish dialog with and without an open round; declining entry sends `enter_competition: false`; entry failure shows the error and re-fetches.

## 10. Clean-up

- [ ] 10.1 Remove `competition_id` from `CreateProjectInput` (`services/project/handler_interface.py:16`) and any caller passing it; `create()` never read it.
- [ ] 10.2 Update `scripts/seed_db.py:591`, `scripts/seed_prod_copy.py:386` and `apps/projects/management/commands/seed_discover_data.py:296` to create `CompetitionEntry` rows with an explicit `entered_via`, since `projects.add()` no longer works on a `through` M2M.
- [ ] 10.3 Update `tests/factories.py:278` (`CompetitionFactory`'s post-generation `projects.add`) the same way, and check every `competition.projects.add(...)` in the test suite still compiles.

## 11. Verify

- [ ] 11.1 `make lint`, `make extra-tests`, `make test` in `src/django-backend/`.
- [ ] 11.2 `make lint`, `make test`, `make build-app`, `make extra-tests` in `src/web-ui/`.
- [ ] 11.3 Run the backfill against a production copy and confirm entry count equals the original M2M row count, then confirm the competition page's project list is unchanged.
- [ ] 11.4 Manual pass, round open: publish a draft with the box ticked, confirm the badge shows it entered; publish a second draft with the box unticked, confirm it shows eligible and the Enter button works.
- [ ] 11.5 Manual pass, no round open: publish a draft, confirm the dialog says so and the project shows `no_open_round`; set a competition to `ACCEPTING_APPLICATIONS` in the admin and confirm the Enter button appears without a redeploy.
- [ ] 11.6 Manual pass: confirm an already-entered project offers no Enter control, and that a community tipoff shows no competition messaging at all.
