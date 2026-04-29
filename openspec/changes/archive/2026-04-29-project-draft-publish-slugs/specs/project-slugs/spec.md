## ADDED Requirements

### Requirement: Projects carry a unique, URL-safe slug

The system SHALL store a `slug` field on each project. For any project with a non-draft status, `slug` SHALL be non-null and unique across all projects. For draft projects, `slug` SHALL be null.

#### Scenario: Slugs are unique across projects

- **WHEN** any two non-draft projects exist in the database
- **THEN** their `slug` values are different

#### Scenario: Drafts have no slug

- **WHEN** a project has `status = DRAFT`
- **THEN** its `slug` is `null`

### Requirement: Slugs are generated from the title at publish time

The system SHALL generate a project's slug at the moment of publish by applying the existing Icelandic-to-ASCII transliteration followed by Django's `slugify` to the project's current `title`. If the resulting slug collides with an existing slug, the system SHALL append `-2`, `-3`, and so on, picking the smallest unused suffix.

#### Scenario: Slug generated from a simple title

- **WHEN** a draft titled "Super App" is published and no other project has slug "super-app"
- **THEN** its slug is `"super-app"`

#### Scenario: Slug collision resolved with numeric suffix

- **WHEN** a project with slug `"super-app"` already exists and a new draft titled "Super App" is published
- **THEN** the new project's slug is `"super-app-2"`

#### Scenario: Icelandic characters are transliterated

- **WHEN** a draft titled "Súperþing" is published
- **THEN** its slug is generated with Icelandic characters replaced using the existing `transliterate_icelandic` mapping (e.g. `"superthing"`)

#### Scenario: Non-alphanumeric characters are preserved as dashes

- **WHEN** a draft whose title contains any non-alphanumeric characters (e.g. "boots.is", "my_cool_app", "team/boots", "foo.com/hellothere?x=1") is published
- **THEN** each run of non-alphanumeric characters is treated as a separator before slugification, so the resulting slug preserves word boundaries (`"boots-is"`, `"my-cool-app"`, `"team-boots"`, `"foo-com-hellothere-x-1"`) rather than silently dropping the punctuation and collapsing the words together

### Requirement: Slugs are immutable after publish

The system SHALL NOT regenerate or modify a project's slug after publish, even when the owner edits the project's title or other fields.

#### Scenario: Editing title after publish does not change slug

- **GIVEN** a published project with `title = "Old Name"` and `slug = "old-name"`
- **WHEN** the owner updates the title to "New Name" via `PUT /api/my-projects/{id}`
- **THEN** the project's slug remains `"old-name"`

#### Scenario: Resubmit does not change slug

- **GIVEN** a rejected project with `slug = "some-slug"`
- **WHEN** the owner resubmits the project
- **THEN** the slug remains `"some-slug"`

### Requirement: Public project URLs use slugs

The web UI SHALL address published projects under `/projects/{slug}` in public contexts.

#### Scenario: Internal links use slug URLs

- **WHEN** any internal listing (featured, new arrivals, winners, most discussed, by category, discover) renders a link to a published project
- **THEN** the link target is `/projects/{slug}` using the project's canonical slug

### Requirement: Legacy UUID URLs 301 to the slug URL

The web UI SHALL accept the legacy `/projects/{uuid}` URL shape and, for any request whose URL identifier does not match the canonical slug of the referenced project, issue a permanent (HTTP 301) redirect to `/projects/{slug}`.

#### Scenario: Request to a UUID URL redirects to slug

- **WHEN** a browser requests `/projects/3f2a0c...` where that UUID identifies a published project with slug `"cool-app"`
- **THEN** the response is a 301 redirect to `/projects/cool-app`

#### Scenario: Request to an already-canonical slug renders

- **WHEN** a browser requests `/projects/cool-app` and that slug identifies a published project
- **THEN** the page renders the project (no redirect)

#### Scenario: Unknown identifier returns 404

- **WHEN** a browser requests `/projects/does-not-exist` where the identifier matches no project
- **THEN** the response is a 404

### Requirement: Public project endpoint accepts either slug or UUID

The Django backend SHALL expose `GET /api/projects/{identifier}` that resolves `identifier` as either a slug or a UUID, returning the same project representation in both cases. The response body SHALL always include the project's canonical `slug`.

#### Scenario: Lookup by slug

- **WHEN** a client calls `GET /api/projects/cool-app`
- **AND** a published project with that slug exists
- **THEN** the response is `200` with the project, and `response.slug == "cool-app"`

#### Scenario: Lookup by UUID

- **WHEN** a client calls `GET /api/projects/{uuid}` and that UUID identifies a published project with slug `"cool-app"`
- **THEN** the response is `200` with the project, and `response.slug == "cool-app"`

#### Scenario: Draft is not returned to non-owners

- **WHEN** an unauthenticated client or a non-owner calls `GET /api/projects/{identifier}` for a draft project
- **THEN** the response is `404`

#### Scenario: Unknown identifier

- **WHEN** a client calls `GET /api/projects/{identifier}` and no project matches the identifier by slug or UUID
- **THEN** the response is `404`
