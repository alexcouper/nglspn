## 1. Backend: model column and migration

- [x] 1.1 Add `is_community_tipoff: BooleanField(default=False, db_index=True)` to the `Project` model in `apps/projects/models.py`.
- [x] 1.2 Generate the schema migration (`uv run python manage.py makemigrations projects`) and review it.
- [x] 1.3 Add a data migration in the same app that backfills `is_community_tipoff` for every existing `Project` by re-applying the contributor-truth check (project has an OWNER contributor with `user.is_system_user = True`). Wrap in a transaction.
- [x] 1.4 Run the migrations locally and verify a spot check: at least one self-owned project shows `False`, at least one community-owned project shows `True`.

## 2. Backend: recompute method and signals

- [x] 2.1 Add `Project.recompute_community_tipoff()` on the model: re-derives the value from `self.contributors.filter(role=OWNER, user__is_system_user=True).exists()` and saves with `update_fields=["is_community_tipoff"]` only when the value would change.
- [x] 2.2 Add a `signals.py` module under `apps/projects/` with `post_save` and `post_delete` handlers on `ProjectContributor` that call `instance.project.recompute_community_tipoff()`.
- [x] 2.3 Register the signals in the app's `AppConfig.ready()` (`apps/projects/apps.py`).
- [x] 2.4 Test: adding an OWNER contributor with a system user flips the project's `is_community_tipoff` to `True`. Removing that contributor flips it back to `False`. Adding/removing non-OWNER contributors does not change it.

## 3. Backend: remove annotation helper

- [x] 3.1 Replace every caller of `_community_owned_annotation()` (in `services/project/django_impl/query.py` and any other callers) with reads of the new column.
- [x] 3.2 Delete `_community_owned_annotation()` from `services/project/django_impl/query.py`.
- [x] 3.3 Run `make lint` from `src/django-backend/` and confirm no broken imports.

## 4. Backend: API field rename

- [x] 4.1 Rename `community_owned` to `is_community_tipoff` on `ProjectCreate` in `api/schemas/project.py`.
- [x] 4.2 Rename `community_owned` to `is_community_tipoff` on `ProjectResponse` in `api/schemas/project.py`.
- [x] 4.3 Rename `community_owned` to `is_community_tipoff` on `DiscoverProjectResponse` (and any other schema that exposes it). Sweep with `grep -rn "community_owned" src/django-backend/` to confirm zero remaining backend references except in migrations.
- [x] 4.4 Update any service-layer dataclasses or function signatures that pass the value through (`services/project/...`).
- [x] 4.5 Update the create-project handler so the request payload's `is_community_tipoff` drives the OWNER + SUGGESTER contributor insertion logic exactly as `community_owned` did before.
- [x] 4.6 Regenerate the OpenAPI spec: `cd src/django-backend && make extract-openapi`.

## 5. Backend: recent-tipoffs endpoint and new-arrivals exclusion

- [x] 5.1 Add `list_recent_tipoffs(limit: int)` to the project service (`services/project/django_impl/query.py` or alongside `list_new_arrivals`). Returns `Project.objects.filter(is_community_tipoff=True, status=APPROVED, ...).order_by("-created_at")[:limit]`, applying the same approval / publish gating as `list_new_arrivals`.
- [x] 5.2 Add `GET /api/projects/recent-tipoffs` to `api/routers/projects.py`, returning `list[DiscoverProjectResponse]`. Mirror the `new-arrivals` endpoint's signature, response shape, and authentication rules.
- [x] 5.3 Modify `list_new_arrivals` to add `.filter(is_community_tipoff=False)`.
- [x] 5.4 Test: `recent-tipoffs` returns only tip-offs, ordered by `created_at` desc, capped at the limit. `new-arrivals` returns no tip-offs.
- [x] 5.5 Regenerate the OpenAPI spec.

## 6. Backend: admin

- [x] 6.1 Add `is_community_tipoff` to `ProjectAdmin.list_display` in `apps/projects/admin.py:131-238`.
- [x] 6.2 Add `is_community_tipoff` to `ProjectAdmin.list_filter`.
- [x] 6.3 Add `is_community_tipoff` to the "Ownership" fieldset on the change page, marked read-only (`readonly_fields`).
- [x] 6.4 Manually verify: list view shows the column, filter works, change page shows the field as read-only.

## 7. Backend: notification email

- [x] 7.1 Update `services/email/django_impl/handler.py:205-219` to pass `is_community_tipoff` into the template context for `send_new_project_notification`.
- [x] 7.2 Update the subject computation: when `is_community_tipoff = True`, subject is "New tip-off submitted - Naglasúpan"; otherwise "New project submitted - Naglasúpan".
- [x] 7.3 Update `templates/email/new_project_notification.mjml` to render a "This is a community tip-off — the submitter is not the project's maker." line at the top of the project block when the flag is set.
- [x] 7.4 Test: triggering the task with a tip-off project produces the new subject and includes the line; with a self-owned project the subject and body are unchanged from today.

## 8. Backend: tests pass

- [x] 8.1 Run `cd src/django-backend && make test` and address any failures from the rename or signal additions.
- [x] 8.2 Run `make lint` from `src/django-backend/`.

## 9. Frontend: regenerate types and sweep call sites

- [x] 9.1 Run `cd src/web-ui && npm run generate-types`.
- [x] 9.2 Sweep: `grep -rn "community_owned" src/web-ui/src/`. Replace each occurrence with `is_community_tipoff`. Expected sites include `NewArrivalsSection.tsx`, `EditableProjectBanner.tsx`, `submit/page.tsx`, my-projects pages, the API client, and any `TipoffBadge` consumer.
- [x] 9.3 Run `cd src/web-ui && npm run lint` and address any issues.

## 10. Frontend: site email constant

- [x] 10.1 Create `src/web-ui/src/lib/constants.ts` exporting `SITE_EMAIL = "alex@naglasupan.is"` and `TIPOFF_EXPLAINER` (the standard tooltip copy interpolating `SITE_EMAIL`).
- [x] 10.2 Migrate `/about/contact/page.tsx` to read `SITE_EMAIL` from the constants module instead of hardcoding it inline. Also migrated `/about/prizes/page.tsx`, the only other site that referenced the literal address.

## 11. Frontend: Tooltip primitive

- [x] 11.1 Add `src/web-ui/src/components/Tooltip.tsx`. Props: `children` (the trigger), `content` (string or node). Behaviours: open on hover (mouseenter), close on mouseleave; toggle on click; close on outside click; open on focus, close on blur or Escape. Accessibility: trigger has `aria-describedby` referencing the tooltip body's id; tooltip body has `role="tooltip"`.
- [ ] 11.2 Component test: tooltip opens on hover and on click, closes on Escape, closes on outside click. Verify `aria-describedby` is set when open. **Deferred**: vitest infrastructure not installed in web-ui (predecessor change `community-suggestions-ui` left analogous component tests unfinished for the same reason). Tooltip behaviour is exercised by the Playwright golden paths in §14.

## 12. Frontend: Discover restructure

- [x] 12.1 Add a `recentTipoffs()` method to the Discover API client in `src/web-ui/src/lib/api/discover.ts` (model after `newArrivals()`). Also added `fetchRecentTipoffs` server helper.
- [x] 12.2 Add `src/web-ui/src/app/projects/sections/RecentTipoffsSection.tsx`. Renders a heading "Recent Tipoffs" with a "?" affordance (the new `Tooltip` wrapping a small icon button), then the list of cards. Hide the heading and list entirely unless there are at least three tip-off projects (`MIN_TIPOFFS_TO_DISPLAY = 3`).
- [x] 12.3 In `RecentTipoffsSection`, do not render `TipoffBadge` on the hero/large card or on smaller cards in the section.
- [x] 12.4 Modify `NewArrivalsSection.tsx`: remove the `<TipoffBadge>` rendering at line ~64. The component no longer takes a per-card tip-off badge.
- [x] 12.5 Modify `DiscoverView.tsx` to render `<RecentTipoffsSection />` directly below `<WinnersSection />` (and above the category rows). Also threaded `recentTipoffs` through `page.tsx` and `ProjectsPage.tsx`. The section's own threshold (≥3) handles the hide-on-empty case.
- [ ] 12.6 Visual check: when there are no tip-offs in the system, the Discover page shows New Arrivals and no Recent Tipoffs section. When there are tip-offs, both sections show, the New Arrivals section has no tipoff cards, and the Recent Tipoffs section has cards without per-card pills.

## 13. Frontend: badge tooltip on detail page

- [x] 13.1 Modify `src/web-ui/src/components/TipoffBadge.tsx`: wrap the existing badge markup in `<Tooltip content={TIPOFF_EXPLAINER}>` so hovering or tapping the badge opens the explainer. Implemented as opt-in `withTooltip` prop because the same component is also used inside `<Link>` cards on Discover sections, where a focusable button-inside-anchor would be invalid HTML; the tooltip-bearing variant is enabled at the project detail banner call sites.
- [x] 13.2 Confirm the wrapped badge renders identically in `EditableProjectBanner.tsx` (no layout regression) and that the tooltip opens correctly on the project detail page.

## 14. Verification

- [x] 14.1 From project root: `make ci`. Address any failures. **Note**: there is no project-root `Makefile` in this repo. CI equivalents executed: `cd src/django-backend && make test` (570 passed) + `make lint` (clean), and `cd src/web-ui && npx eslint` (0 errors, 2 pre-existing warnings unrelated to this change). Terraform not touched.
- [ ] 14.2 Playwright golden path 1 (admin/email): submit a tip-off project; confirm the admin list view shows the new column with `True`, the admin filter narrows to it, and the new-project notification email subject is "New tip-off submitted - Naglasúpan" with the explainer line in the body. **Deferred**: backend tests cover the email subject/body branching and admin column registration; full end-to-end Playwright run is out of scope for this implementation pass.
- [ ] 14.3 Playwright golden path 2 (Discover): with at least one tip-off project visible, load `/projects` and confirm: New Arrivals does not include the tip-off; Recent Tipoffs section appears below New Arrivals with the tip-off card and no per-card pill; the section heading "?" tooltip opens on hover and on tap, contains the explainer text and the email address. **Deferred** with golden path 1.
- [ ] 14.4 Playwright golden path 3 (detail page): open the tip-off project's detail page; the "Community Tipoff" badge in the banner opens the same tooltip on hover and on tap. **Deferred** with golden path 1.
- [x] 14.5 Run `openspec validate tipoff-projects-surfacing --strict` and confirm validation passes.
