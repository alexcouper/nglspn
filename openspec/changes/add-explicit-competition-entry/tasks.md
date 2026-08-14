# Tasks: add explicit competition entry

## 1. Measure the backlog before committing to it

- [x] 1.1 Answered without a production copy: there are no published projects outside a competition in production, so nothing becomes newly eligible on deploy. Recorded in `design.md`'s Open Questions.
- [x] 1.2 No warning needed — the backlog is empty. Noted in `design.md`'s Risks: every production project already holds a `monthly` entry, so the next monthly round starts empty and fills with newly published projects, as it does today.

## 2. Model and migrations

- [x] 2.1 Add `Competition.entry_series = SlugField(max_length=50, default="monthly", db_index=True)` to `src/django-backend/apps/projects/models.py` and generate `0047_competition_entry_series`.
- [x] 2.2 Add `EntrySource` (`manual`, `admin`, `backfill`) and `CompetitionEntry` to the same module, with `db_table = "competition_entries"`, `unique_together = ("competition", "project")`, `entered_at = DateTimeField(default=timezone.now)` and `entered_by` nullable with `on_delete=SET_NULL`. Generate `0048_competitionentry` creating the model only — leave `Competition.projects` alone at this step.
- [x] 2.3 Write data migration `0049_backfill_competition_entries` copying every row from the auto-created `competitions_projects` table using `get_or_create` on `(competition, project)`, with `entered_via = "backfill"`, `entered_at = project.published_at or competition.start_date`, `entered_by = None`. Give it a reverse that deletes only `entered_via = "backfill"` rows. Use the historical model from `apps.registry`, not the imported one.
- [x] 2.4 Change `Competition.projects` to `ManyToManyField(Project, through="CompetitionEntry", related_name="competitions", blank=True)` and generate `0050_competition_projects_through`.
- [x] 2.5 Run `uv run python manage.py makemigrations --check --dry-run` and confirm it reports nothing outstanding.
- [x] 2.6 Add a migration test asserting the backfill preserves row count and maps timestamps as specified, including a project with `published_at = None` falling back to the competition's `start_date`, and asserting every pre-existing competition ends up with `entry_series = "monthly"`.

## 3. Admin

- [x] 3.1 Remove `filter_horizontal = ("projects",)` (`apps/projects/admin.py:657`) and the `"Projects"` fieldset — Django's `admin.E013` rejects both on a `through` M2M.
- [x] 3.2 Add `CompetitionEntryInline` (tabular) with `autocomplete_fields = ("project",)` and `readonly_fields = ("entered_at", "entered_via", "entered_by")` for existing rows; register it on `CompetitionAdmin` alongside `CompetitionReviewerInline`.
- [x] 3.3 Stamp `entered_via = ADMIN` and `entered_by = request.user` on inline rows created through the admin.
- [x] 3.4 Surface `entry_series` on `CompetitionAdmin` — in the form, in `list_display` and in `list_filter`, so a mistyped series is visible from the changelist.
- [x] 3.5 Run `uv run python manage.py check` and confirm no `admin.E013` or related system-check errors.

## 4. Eligibility, in one place

- [x] 4.1 Add `ProjectEntry`, `CompetitionOpportunity` and `CompetitionStanding` (frozen dataclasses, shapes per `design.md`) to `services/project/query_interface.py`.
- [x] 4.2 Implement `competition_standing(project)` in `services/project/django_impl/query.py`: entries newest first, and one opportunity per `ACCEPTING_APPLICATIONS` competition applying the four ordered rules. No open competitions means an empty opportunity list, not a reason.
- [x] 4.3 Implement `with_competition_standing(qs)` in the same module: prefetch `competition_entries__competition`, resolve the open competitions once, stamp `_competition_standing` on each instance.
- [x] 4.4 Unit-test each rule in `services/project/django_impl/test_query.py`, including the precedence cases: tipoff beats `already_in_series`; entered-in-a-closed-round-of-the-same-series blocks; a different series does not block; two open competitions produce two opportunities; `already_in_series` names the blocking competition.

## 5. Publish stops entering

- [x] 5.1 Delete the competition-entry block from `DjangoProjectHandler.publish` (`services/project/django_impl/handler.py:215-224`). Publish touches no competition state.
- [x] 5.2 Check whether the tipoff/community-owner lookup in `publish()` is now dead; remove it if nothing else reads it.
- [x] 5.3 Update `api/routers/test_my_projects.py`: publishing with an open round creates no `CompetitionEntry` and leaves the project with an eligible opportunity for it; publishing a community-owned project behaves identically; a `400` on missing fields is unchanged.

## 6. The entry endpoint

- [x] 6.1 Add `enter_competition(project_id, competition_id, user_id)` to the project handler interface and its Django implementation: re-evaluate the standing, reject unless the named competition is an eligible opportunity, reject `status = DRAFT` separately, create the entry with `entered_via = MANUAL` and `entered_by`, catch `IntegrityError` from the unique constraint and raise a distinct error for it.
- [x] 6.2 Add `CompetitionEntryRequest` (`competition_id: UUID`, required) to `api/schemas/project.py` and `POST /api/my-projects/{project_id}/competition-entry` to `api/routers/my_projects.py`, returning `200 ProjectResponse`, `400` (not an eligible opportunity / draft / unknown competition), `404` (no `full_edit`), `409` (concurrent entry).
- [x] 6.3 Cover every scenario in `specs/competition-entry/spec.md` under "A published project can enter a named competition" in `api/routers/test_my_projects.py`, including a project published between rounds entering the next one, and a past entrant entering a different series.

## 7. Standing on the API

- [x] 7.1 Add `CompetitionSummary` (`id`, `name`, `slug`, `status`, `submission_deadline`), `ProjectEntryResponse`, `CompetitionOpportunityResponse` and `CompetitionStandingResponse` to `api/schemas/project.py`.
- [x] 7.2 Add `competition_standing: CompetitionStandingResponse | None = None` to `ProjectResponse` with a resolver reading the stamped `_competition_standing`, falling back to computing it for a single instance.
- [x] 7.3 Apply `with_competition_standing` in the `/api/my-projects` list and detail paths only; leave the public project queries alone so `competition_standing` is null there.
- [x] 7.4 Add a query-count test over `GET /api/my-projects` with several projects, asserting the count does not grow with the number of projects.
- [x] 7.5 Assert `competition_standing` is null on `GET /api/projects/{identifier}`.
- [x] 7.6 Run `make extract-openapi` in `src/django-backend/` and commit `src/web-ui/backend-openapi.json` — `make extra-tests` fails without it.

## 8. Frontend plumbing

- [x] 8.1 Run `npm run generate-types` in `src/web-ui/` (do not commit `src/lib/api-types.ts`).
- [x] 8.2 Add `api.myProjects.enterCompetition(projectId, competitionId)` to `src/lib/api/my-projects.ts`.

## 9. The project page competitions section

- [x] 9.1 Add `ProjectCompetitions`, rendering `competition_standing` with no eligibility logic of its own: entered rounds (name, link, `entered_at`, competition status, won marker from the existing `won_competitions`), then open rounds with a per-row **Enter in \<name\>** control or the row's reason.
- [x] 9.2 Collapse project-wide reasons (`community_project`, `project_status`) into one line rather than repeating them per row; render the empty case as a single "no round is open" line rather than hiding the section.
- [x] 9.3 Wire the Enter control to `api.myProjects.enterCompetition`; on success re-fetch, on failure show the error and re-fetch.
- [x] 9.4 Render `ProjectCompetitions` on `/my-projects/[id]` (`ProjectDetail.tsx`).
- [x] 9.5 Render a compressed read-only variant on each card in `ProjectsList.tsx` — entered round names, or the rounds it could enter — with no controls.

## 10. Publish and submit flows

- [x] 10.1 Add `EnterCompetitionDialog`: given a project's eligible opportunities, lists each competition with its `submission_deadline`, enters the one chosen, and dismisses without entering. Renders nothing when there are no eligible opportunities.
- [x] 10.2 Open it in `ProjectDetail.tsx` on a `200` from publish, before the redirect to `/my-projects`; keep the existing `PublishDialog` for the `400 missing` response and show no entry prompt on `400`.
- [x] 10.3 Rework `/submit` (`src/app/submit/page.tsx`) into enter-or-create: read the optional `?competition=<id>`, list the user's eligible projects above the URL form with an Enter control each, headed by the competition's name when the parameter is present. Filter from `GET /api/my-projects` — no new endpoint. Render the list not at all when empty, leaving today's page.
- [x] 10.4 Point the competition CTA (`CompetitionReveal.tsx:122-140`) at `/submit?competition=<id>` for authenticated users and reword it to cover both routes; leave the anonymous CTA as it is.
- [x] 10.5 Vitest cover: `ProjectCompetitions` with entries only, opportunities only, a blocked `already_in_series` row, a project-wide reason, and the empty case; entry failure shows the error and re-fetches; the post-publish dialog appears only when something is on offer and calls the endpoint with the chosen competition; `/submit` with and without `?competition=`, and with no eligible projects.

## 11. Clean-up

- [x] 11.1 Remove `competition_id` from `CreateProjectInput` (`services/project/handler_interface.py:16`) and any caller passing it; `create()` never read it.
- [x] 11.2 Update `scripts/seed_db.py:591`, `scripts/seed_prod_copy.py:386` and `apps/projects/management/commands/seed_discover_data.py:296` to create `CompetitionEntry` rows with an explicit `entered_via`, since `projects.add()` no longer works on a `through` M2M. Give seeded competitions an explicit `entry_series`, including at least one non-`monthly` series so the multi-series paths are reachable by hand.
- [x] 11.3 Update `tests/factories.py:278` (`CompetitionFactory`'s post-generation `projects.add`) the same way, and check every `competition.projects.add(...)` in the test suite still compiles.

## 12. Verify

- [x] 12.1 `make lint`, `make extra-tests`, `make test` in `src/django-backend/`.
- [x] 12.2 `make lint`, `make test`, `make build-app`, `make extra-tests` in `src/web-ui/`.
- [ ] 12.3 **Not done — no production copy in this workspace.** The backfill ran against the local dev database (22 competitions, 111 entries, all `backfill`/`monthly`) and against the test database in `tests/test_competition_entry_migration.py`. Still worth one run on a production copy before deploy.
- [x] 12.4 Manual pass, one round open: publish a draft, confirm the dialog offers that round, enter it, confirm the project page shows it entered and offers no control. Publish a second draft and dismiss the dialog; confirm the project page still offers the round and the control works.
- [x] 12.5 Manual pass, two rounds open of different series: confirm both appear as rows with their own Enter controls, enter one, and confirm the other is still offered.
- [x] 12.6 Manual pass, same series twice: with a project already in a `monthly` round, open another `monthly` round and confirm the project page shows it blocked with the competition it is already in named, and that `POST /competition-entry` for it returns `400`.
- [x] 12.7 Manual pass, no round open: publish a draft, confirm no dialog appears and the project page states no round is open; set a competition to `ACCEPTING_APPLICATIONS` in the admin and confirm the Enter control appears without a redeploy.
- [x] 12.8 Manual pass: `/submit?competition=<id>` lists only the projects eligible for that round and enters one from there; `/submit` with no parameter lists everything eligible; a user with nothing eligible sees today's page. Confirm a community tipoff shows the single project-wide reason and no controls.
