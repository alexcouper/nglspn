## Context

This is the third in the Community Submissions trio. By the time this change is implemented:

- The backend exposes `creator: UserSummary` and `contributors: list<{user, role, full_edit}>` on every project response.
- `POST /api/my-projects` accepts an optional `community_owned: boolean` flag.
- `GET /api/my-projects/suggestions` returns projects where the caller is a `SUGGESTER`.
- A `Community/Unowned` user exists with `is_system_user = true` and is reachable via the `contributors` list as an OWNER.

The frontend currently:

- Renders the project page's title banner with author name + email (see `ProjectTitleBanner.tsx`) sourced from `project.owner`.
- Has a `/submit` page (and likely an in-page submit affordance under `/my-projects`) that posts to `POST /api/my-projects` without any community-ownership concept.
- Has a `/my-projects` listing that shows the projects returned by `GET /api/my-projects` as a flat list (`ProjectsList.tsx`).

This change is intentionally narrow: only the affordances that surface community submissions in the UI. No structural reshuffles, no styling overhauls.

## Goals / Non-Goals

**Goals:**
- Add the create-form "I own this project" checkbox with a default of *checked* and the natural mapping to `community_owned`.
- Render community-owned projects in `/my-projects` under a separate "Suggested" heading, hidden when there are none.
- Hide the "by {owner}" line on the project detail title banner when the only OWNER contributors are system users.
- Display "Suggested by {creator}" / "Created by {creator}" below the project tags so the human submitter is visible without taking the top spot.
- Migrate any remaining `project.owner` reads to `project.creator` (or contributor-derived values) so the UI matches the renamed schema.

**Non-Goals:**
- Any styling redesign of the project page beyond what these requirements dictate.
- A future "claim this project" button.
- Highlighting or distinguishing SUGGESTER contributors visually beyond the credit line — they're just credit-line attributions in this change.
- Pagination for the Suggested section.
- Empty-state copy beyond hiding the section.

## Decisions

### 1. Default the checkbox to *checked* (= "I own this")

Most submissions today are self-owned, and we want the default behaviour to remain identical for users who don't read the checkbox carefully. Sending `community_owned: false` (or omitting it) preserves the existing flow.

Inverting the default would surface community submissions more prominently, but at the cost of nudging confused users into mis-attributing their own work to the Community/Unowned placeholder.

### 2. Banner author rendering: OWNER contributors with full edit

The current banner reads `project.owner.name`. The new rule:

- Compute `displayOwners = project.contributors.filter(c => c.role === "OWNER" && c.full_edit && !c.user.is_system_user)`.
- If `displayOwners.length === 0`, omit the "by ..." line entirely. Title, tagline, URL remain.
- If `displayOwners.length >= 1`, render a comma-joined list of their names (linked to their profile, as today). For now there's at most one — group-owned projects later may produce more.

Note that `is_system_user` will need to be present on the `UserSummary` payload for this filter to work client-side. If the backend's `UserSummary` does not yet include it, we add it as part of this change's regeneration step (or treat it as a small backend follow-up — see Open Questions).

### 3. Credit line below tags

A second-prominence line, below the project tags / metadata area, of the form:

- `Suggested by {creator.name}` when `creator.id` is not the id of any contributor in `displayOwners` (i.e. the creator is *not* one of the visible owners — community submissions).
- `Created by {creator.name}` otherwise (regular self-owned project — creator and owner coincide).

Both are linked to the creator's profile if profile pages exist; otherwise plain text.

### 4. Suggested section is a sibling of the existing list

In `ProjectsList.tsx` (or its parent page), fetch `GET /api/my-projects/suggestions` in parallel with the existing my-projects fetch. Render two sections:

- "My Projects" — the existing list, unchanged. Header always visible (or hidden-when-empty by current behaviour, which we preserve).
- "Suggested" — the new list. Header AND list are hidden if the response is an empty array.

Reuse the existing project card component. Each card may visually mark community-owned projects (e.g. a small "Suggested" badge) to distinguish them from self-owned projects in the same view; if the card already takes a `creator` and `contributors` prop, the badge can be derived. Keeping this badge minimal in scope: a tiny tag or icon, not a redesign.

### 5. Migrate `project.owner` reads to `project.creator`

Any remaining `project.owner.*` reads in the codebase (search hits in `ProjectTitleBanner.tsx`, `ProjectsList.tsx`, `ProjectDetail.tsx`, `EditProjectContent.tsx`, etc.) are replaced with the appropriate new field:

- "Show me who created this" → `project.creator`.
- "Show me who can act on this" → `project.contributors[]`.

If the backend retained an `owner` field in the response for one cycle (see `multi-contributor-projects` design Decision 5), the FE explicitly migrates off of it in this change, paving the way for a later backend-only cleanup that removes it.

### 6. Don't fetch the seed user separately

The contributor list already contains the seed user when the project is community-owned (as an OWNER). The FE does not need any new endpoint or hardcoded id; it consults `contributors[].user.is_system_user` directly. This keeps coupling minimal.

## Risks / Trade-offs

- **[Risk] `is_system_user` not on the `UserSummary` schema.** The contributor filter relies on the FE knowing, per contributor, whether the user is a system user. → Mitigation: confirm during implementation that the regenerated types include `is_system_user` on user summaries; if not, add it in a small backend tweak as part of this change (acceptable because it's a serializer-only change with a generated-types update).
- **[Risk] Mis-categorising regular projects as suggestions.** A subtle off-by-one in the `displayOwners` filter (e.g. forgetting to require `full_edit`) could hide owners on regular projects. → Mitigation: a focused component test that asserts the banner renders the owner line for a regular project where `creator === only OWNER === full_edit=true`.
- **[Risk] The badge on suggestion cards adds visual clutter.** → Acceptable: the badge is small and only appears in the "Suggested" section, where context already implies community-suggested. We may even drop the badge if the section header is enough.
- **[Trade-off] Two API calls on the my-projects page.** → Acceptable: both endpoints are scoped to the calling user and indexed; latency impact is negligible in practice.
- **[Risk] Submit form's checkbox is buried/invisible.** → Mitigation: place it directly under the URL field with a one-line helper text ("Untick if you didn't make this project — it'll be added as a community submission"). Real copy decided during implementation.

## Migration Plan

This is a frontend-only change with no migrations to run. Steps:

1. Verify generated types include `community_owned`, `creator`, `contributors[]`, and `is_system_user` on user summaries. Regenerate if stale.
2. Add the checkbox to the create form; thread it into the API call payload.
3. Refactor the title banner to use `displayOwners` logic.
4. Add the credit line component and slot it under tags.
5. Add the Suggested section to the my-projects page, fetching the new endpoint.
6. Sweep remaining `project.owner` references and replace.
7. Run `npm run lint` and any existing tests; do a Playwright pass on the golden paths.

Roll-back: revert the frontend commits. No backend changes to roll back.

## Open Questions

- Final placement of the "Suggested" section — above or below "My Projects"? Defaulted to *below* (creator's own work is the primary surface). Trivial to flip.
- Final copy for the checkbox helper text. Defaulted to "Untick if you didn't make this project — it'll be added as a community submission."
- Should the Suggested cards visually differ from My Projects cards beyond the section heading? Defaulted to a small "Suggested" badge in the upper corner of each card, derived from the project's contributor list.
- Do we want a tooltip on the omitted top-bar owner line for community-owned projects (e.g. "Owner unknown — this is a community-suggested project")? Defaulted to *no tooltip* to keep the line genuinely silent; the credit line below carries the suggestion attribution.
