## Context

The Competition model currently has `start_date` and `end_date` fields. With the introduction of a voting phase (`PENDING` -> `ACCEPTING_APPLICATIONS` -> `VOTING` -> `CLOSED`), `end_date` is ambiguous — it could mean "submissions close" or "competition ends". The frontend uses `end_date` for all "days remaining" and "time since" calculations, producing incorrect results during the voting phase.

The homepage currently fetches a single active + single recent competition via `active-or-most-recent`. With multiple competitions potentially active simultaneously (one accepting, one voting), this endpoint needs to return a list.

## Goals / Non-Goals

**Goals:**
- Clear, unambiguous date semantics for each competition phase
- Homepage displays all active competitions plus the 1 most recently closed
- Context-aware deadline display across all frontend components
- Backward-compatible data migration (no data loss)

**Non-Goals:**
- Automated status transitions based on dates (status remains manually controlled via admin)
- Pagination or infinite scroll for the homepage carousel
- Changes to the review system's date handling beyond the field rename

## Decisions

### 1. Rename `end_date` to `submission_deadline` via Django migration

**Rationale:** A rename (using `RenameField`) preserves data without a copy-and-delete cycle. `submission_deadline` is unambiguous about what the date means. Considered keeping `end_date` and just adding `voting_end_date`, but that leaves the naming inconsistent and confusing for future developers.

### 2. `voting_end_date` is nullable

**Rationale:** Not all competitions may have a voting phase (e.g., future competition formats). Nullable allows the field to be optional. For existing competitions, the data migration sets `voting_end_date = submission_deadline` as a sensible default. The frontend falls back to `submission_deadline` when `voting_end_date` is null.

### 3. Replace `active-or-most-recent` with a list-based endpoint

Current response shape: `{ active: Summary | null, recent: Summary | null }`
New response shape: `{ competitions: Summary[] }`

Query logic:
1. Fetch all competitions with status `ACCEPTING_APPLICATIONS` or `VOTING`, ordered by `start_date` descending (newest first)
2. Fetch the 1 most recently closed competition, ordered by `voting_end_date` descending (falling back to `submission_deadline`)
3. Concatenate: active competitions first, then the closed one

**Rationale:** A list is simpler than separate nullable fields and naturally supports 0..N active competitions. The frontend carousel iterates the list without needing to know about active vs. recent distinction — it just renders cards in order.

### 4. Reuse `HorizontalScroll` component from discover page

**Rationale:** The discover page already has a well-built `HorizontalScroll` wrapper (`src/web-ui/src/app/projects/HorizontalScroll.tsx`) with native `overflow-x-auto`, gradient fade indicators, and ResizeObserver-based edge detection. Competition cards will be rendered as fixed-width items inside this wrapper, consistent with how NewArrivals, Winners, and CategoryRows sections work on the discover page. No dots or scroll-snap needed — the gradient fades provide sufficient visual feedback. The component should be moved from `app/projects/` to `components/` since it's now shared across pages.

### 5. `CompetitionSummaryResponse` gains `submission_deadline` and `voting_end_date`

The summary schema currently only has `end_date`. It will gain both date fields so the frontend can compute the right deadline per status. `start_date` is not needed in the summary — it's only used for sorting on the backend.

## Risks / Trade-offs

- **Field rename is a breaking API change** -> All API consumers must update simultaneously. Since the only consumer is our own frontend (types are auto-generated), this is low risk. Deploy backend and regenerate types in the same release.
- **`voting_end_date` null ambiguity** -> Frontend must handle the null case. Mitigation: when `voting_end_date` is null and status is `voting`, fall back to `submission_deadline`. Admin validation could enforce non-null when status is `voting`, but that's a non-goal for now.
- **Single competition** -> With only 1 item the `HorizontalScroll` wrapper still works fine — no gradient fades appear since there's nothing to scroll, so it naturally degrades to a single card.

## Migration Plan

1. Create migration: `RenameField` for `end_date` -> `submission_deadline`, `AddField` for `voting_end_date`
2. Data migration: set `voting_end_date = submission_deadline` for all existing rows
3. Update all backend code (model, schemas, routers, admin, services, tests, seeds)
4. Regenerate OpenAPI spec and frontend types
5. Update all frontend components
6. No rollback complexity — if needed, reverse migration renames field back
