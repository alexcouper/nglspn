# community-suggestions-ui Specification

## Purpose

Frontend UI for community-suggested projects: allowing users to submit projects they don't own as community submissions, surfacing suggested projects in the my-projects page, and deriving owner/creator credits on the project detail page from contributors rather than a top-level owner field.

## Requirements

### Requirement: Submit form has an "I own this project" checkbox

The project submit form (currently rendered on the my-projects "create new project" affordance and the standalone `/submit` page if present) SHALL include a checkbox labelled "I own this project". The checkbox SHALL be checked by default.

When the user submits the form:

- If the checkbox is checked, the request to `POST /api/my-projects` SHALL omit `community_owned` (or send `false`).
- If the checkbox is unchecked, the request SHALL include `community_owned: true`.

The checkbox SHALL be accompanied by helper text explaining the consequence of unchecking, e.g. "Untick if you didn't make this project — it'll be added as a community submission". The exact copy is implementation-time and may be refined.

#### Scenario: Default submit creates a self-owned project

- **GIVEN** the user opens the submit form
- **WHEN** they enter a `website_url` and submit without altering the checkbox
- **THEN** the API call is `POST /api/my-projects` with the URL and either no `community_owned` field or `community_owned: false`

#### Scenario: Unticked checkbox creates a community submission

- **GIVEN** the user opens the submit form
- **WHEN** they enter a `website_url`, untick "I own this project", and submit
- **THEN** the API call is `POST /api/my-projects` with `community_owned: true`

#### Scenario: Checkbox state survives field-level validation errors

- **GIVEN** the user has unticked the checkbox and entered an invalid URL
- **WHEN** the form is re-rendered with a validation error
- **THEN** the checkbox remains unticked

### Requirement: My-projects page shows a Suggested section

The `/my-projects` page SHALL render two sections:

1. The existing "My Projects" list, populated by `GET /api/my-projects` (unchanged from prior behaviour — projects where the calling user is `creator`).
2. A new "Suggested" section, populated by `GET /api/my-projects/suggestions`.

The Suggested section's header AND list SHALL be entirely hidden when the suggestions response is an empty array. The page SHALL fetch both endpoints when loading.

#### Scenario: User with no suggestions does not see the Suggested section

- **GIVEN** an authenticated user has no community-suggested projects
- **WHEN** they navigate to `/my-projects`
- **THEN** the "Suggested" header is not rendered
- **AND** no empty-state copy for suggestions is shown

#### Scenario: User with suggestions sees them in the Suggested section

- **GIVEN** an authenticated user has two community-suggested projects
- **WHEN** they navigate to `/my-projects`
- **THEN** the "Suggested" section header is rendered
- **AND** both projects appear under it
- **AND** they do not also appear in the "My Projects" section unless the user is the creator (in this change's data model, every suggester is also the creator, so they DO appear in both — see scenario below)

#### Scenario: A user's own community submission appears in both sections

- **GIVEN** an authenticated user has submitted one community-owned project
- **WHEN** they navigate to `/my-projects`
- **THEN** that project appears in "My Projects" (because they are the `creator`)
- **AND** that project also appears in "Suggested" (because they are a `SUGGESTER` contributor with `full_edit = true`)
- **AND** in "My Projects" the card visually indicates the project is community-suggested (e.g. via a small badge derived from `contributors[].user.is_system_user` on any OWNER)

### Requirement: Project detail page hides the owner line for system-only OWNERs

On the project detail title banner, the rendering of the project's owner / author line SHALL be derived from the project's contributors list rather than a top-level owner field. Specifically, the displayed owners SHALL be the set of contributors satisfying ALL of:

- `role = "OWNER"`
- `full_edit = true`
- `user.is_system_user = false`

If that set is empty (i.e. the project's only OWNER contributors are system users), the "by ..." line SHALL be omitted entirely. The title, tagline, and URL areas of the banner remain unchanged in either case.

If the set has one or more entries, their names SHALL be rendered as before (linked to profile if available), comma-separated for multiple.

#### Scenario: Self-owned project shows the creator on the banner

- **GIVEN** a project whose only OWNER contributor is a non-system user
- **WHEN** the project detail page is rendered
- **THEN** the title banner shows "by {owner name}" linked to the owner's profile
- **AND** the title, tagline, and URL render as today

#### Scenario: Community-owned project hides the owner line

- **GIVEN** a project whose only OWNER contributor is the Community/Unowned system user
- **WHEN** the project detail page is rendered
- **THEN** the title banner does not show any "by ..." line
- **AND** the title, tagline, and URL still render

### Requirement: Project detail page shows a creator credit below the metadata area

The project detail page SHALL display a small credit line below the project's tags / metadata area, of the form:

- "Suggested by {creator name}" when the project's `creator` is not present in the displayed-owner set described above (community submissions).
- "Created by {creator name}" otherwise.

The credit line SHALL link to the creator's profile if profile pages exist, and otherwise render as plain text.

#### Scenario: Self-owned project shows "Created by ..." below tags

- **GIVEN** a project whose `creator` is also its only displayed OWNER
- **WHEN** the project detail page is rendered
- **THEN** below the tags / metadata area, the credit reads "Created by {creator name}"

#### Scenario: Community-owned project shows "Suggested by ..." below tags

- **GIVEN** a community-owned project whose `creator` is the SUGGESTER and whose only OWNER is the system user
- **WHEN** the project detail page is rendered
- **THEN** below the tags / metadata area, the credit reads "Suggested by {creator name}"

### Requirement: No frontend code path relies on a top-level project.owner field

After this change, the frontend SHALL derive any author / owner / creator display from `project.creator` (for the original submitter) or `project.contributors[]` (for the people with edit access). No component SHALL read a top-level `project.owner` field.

#### Scenario: Searching the frontend for `project.owner` returns no UI use

- **WHEN** the codebase is searched for `project.owner` references in `src/web-ui/src/`
- **THEN** any remaining matches are types/imports only (no field reads), or there are no matches at all
