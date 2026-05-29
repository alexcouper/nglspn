## Why

`multi-contributor-projects` reshaped the data model and `community-project-suggestions` exposed the API surface for community submissions, but no user-visible feature exists yet. This change is the frontend layer that lets a real person (a) flag a submission as community-owned at create time, (b) see their suggestions on the my-projects page, and (c) have project pages render the new ownership reality cleanly — including hiding the "by owner" line when the project's only owner is the Community/Unowned placeholder.

The split lets us ship and verify the backend independently, then bring the UI online with a focused, frontend-only change that touches no Django code.

## What Changes

- **Add** an "I own this project" checkbox to the project creation form on the my-projects page (or wherever projects are submitted today). Defaults to checked. When unchecked, the create request includes `community_owned: true`; when checked, the flag is omitted (server default `false` applies).
- **Add** a "Suggested" section to `/my-projects` that lists the projects returned by `GET /api/my-projects/suggestions`. The section header and list SHALL be hidden when the suggestions list is empty.
- **Modify** the project detail page top area: the existing rendering of "by {owner name}" SHALL render the project's full-edit OWNER contributors instead of the project's `creator`. When all OWNER contributors are system users (i.e. the only OWNER is the Community/Unowned placeholder), the "by ..." line SHALL be omitted entirely. The title, tagline, and url remain in place; the rest of the banner layout is unchanged.
- **Add** a creator credit line below the project's tags / metadata area on the project detail page, of the form "Suggested by {creator name}" when the project's creator differs from any OWNER contributor (community submissions), or "Created by {creator name}" otherwise. This makes the original submitter visible without putting them in the top bar.
- **Update** any existing frontend uses of `project.owner` to consume `project.creator` (or `project.contributors[]`) consistently with the renamed and extended API. After this change, no UI code path should depend on a top-level `owner` field.

## Capabilities

### New Capabilities
- `community-suggestions-ui`: the create-form checkbox, the my-projects "Suggested" section, the project detail credit-line behaviour for community submissions, and the rule for hiding the OWNER line when only system-user OWNERS exist.

### Modified Capabilities
- `project-page-layout`: the title banner's author rendering changes from "the project's owner" (single user) to "the OWNER contributors with full edit", with the system-user-only fallback. The rest of the layout requirements are unchanged.

## Impact

- **Web UI**: project create form gains a checkbox + state plumbing; my-projects page gains a Suggested section that calls the new API; project detail page (and discussions page, which shares the title banner) consume `creator` and `contributors[]` from the project response and update banner + credit-line rendering.
- **Frontend types**: this change consumes the regenerated types from `community-project-suggestions`. If the backend types are stale at the start, regenerate first.
- **No backend changes**: everything in this change is frontend.
- **Tests**: component tests for the checkbox state, suggestions section visibility (empty / non-empty), and banner / credit rendering paths (self-owned vs community-owned). Manual / Playwright verification of golden paths.
- **Out of scope**: any new backend behaviour; the future "claim" button; group-owned projects; unique rendering for the SUGGESTER role beyond the credit line; anything to do with edit history or version snapshots.
