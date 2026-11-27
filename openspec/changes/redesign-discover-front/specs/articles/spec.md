## ADDED Requirements

### Requirement: Spotlight flag

An Article SHALL have an `is_spotlight` boolean, default false, set only by an admin. Publishing to any channel SHALL NOT set it. On migration, every globally visible article in the house project's `Reviews` channel SHALL be flagged.

#### Scenario: New review is not auto-spotlighted
- **WHEN** an author publishes an article to the house project's `Reviews` channel
- **THEN** `is_spotlight` stays false until an admin sets it

#### Scenario: Admin spotlights an article
- **WHEN** an admin ticks `is_spotlight` on an article in the admin list
- **THEN** the article is returned by `GET /api/articles/spotlight` while it remains globally visible

### Requirement: Recent expiry

An Article SHALL have a nullable `recent_until` datetime, set only by an admin. Once it has passed, the article SHALL drop out of front-page articles and "read next". Nothing else changes: its page, project listing, spotlight and notifications are unaffected.

#### Scenario: A voting call expires
- **GIVEN** "Pick the Grasker winner" with `recent_until` 2 Dec 17:00
- **WHEN** `GET /api/articles/recent` is requested on 3 Dec
- **THEN** the article is not returned
- **AND** its page still renders

### Requirement: Read next tops up from recent articles

When an article's own project or author has fewer other articles than the "read next" slots, the remaining slots SHALL be filled from front-page articles. The current article and articles from the same container are excluded. The footer's "more" link SHALL go to `/projects` when the top-up is the only group.

#### Scenario: Thin container
- **GIVEN** an author-owned article whose author has no other articles
- **WHEN** a reader reaches the end of it
- **THEN** "read next" shows front-page articles from elsewhere, and the "more" link goes to `/projects`

### Requirement: Back control from the front page

An article opened from a Discover card SHALL carry `?from=discover`, and its back control SHALL go to `/projects`. Any other `from` value, including the retired `latest`, SHALL fall back to the article's project or author.

#### Scenario: Retired origin
- **WHEN** a reader opens an old link ending `?from=latest`
- **THEN** the back control goes to the article's project or author page

### Requirement: Public read paths gate on visibility

No public read path SHALL serve an Article that is not globally visible: drafts, articles awaiting review and demoted articles alike. The rule SHALL have one home, `apps/articles/models.py`, expressed both as the `is_globally_visible` property and as a queryset condition. Seeing an article anyway is an authorisation question for the routers. Whether it renders for everyone is decided on the model.

#### Scenario: Property and queryset agree
- **WHEN** every `state` × `global_visibility` combination is checked
- **THEN** `is_globally_visible` and `ArticleQuerySet.globally_visible()` agree on each

#### Scenario: An article awaiting review is not served publicly
- **GIVEN** a published Article A in an approved project with `global_visibility = pending`
- **WHEN** an anonymous client lists the project's articles or requests A by slug
- **THEN** A SHALL be absent from the listing, and the by-slug request SHALL return 404

#### Scenario: A demoted article is not served publicly
- **GIVEN** a published Article A with `global_visibility = demoted`
- **WHEN** an anonymous client lists the project's articles or requests A by slug
- **THEN** A SHALL be absent from the listing, and the by-slug request SHALL return 404

#### Scenario: The author still sees a held-back article in edit mode
- **GIVEN** a published Article A with `global_visibility = pending` or `demoted`
- **WHEN** its author, or a user who can edit the project, lists the project's articles (each item carrying `is_globally_visible`) or requests A by id
- **THEN** A SHALL appear in the listing, and the by-id request SHALL return 200

#### Scenario: Anyone else requesting a held-back article by id
- **GIVEN** a published Article A with `global_visibility = pending`
- **WHEN** a user who is neither its author nor a project editor requests `GET /projects/{slug}/articles/{A.id}`
- **THEN** the request SHALL return 403

#### Scenario: A held-back article is not on the front page
- **GIVEN** a published, spotlighted Article A with `global_visibility = pending`
- **WHEN** the recent or spotlight endpoint is read
- **THEN** A SHALL NOT be returned

#### Scenario: Approving an article puts it on the front page
- **GIVEN** a published Article A with `global_visibility = pending`
- **WHEN** an admin approves it
- **THEN** A SHALL be returned by the recent endpoint, ordered by its new `approved_at`

## REMOVED Requirements

### Requirement: Read paths gate on `is_globally_visible`
**Reason**: Its rule and scenarios were written around the Latest feed, which is removed. Replaced by "Public read paths gate on visibility", which carries the same gates over to the front-page endpoints.
**Migration**: None. Behaviour for project listings and article reads is unchanged.

### Requirement: Article publish appends a feed event
**Reason**: The feed is removed. The front page reads articles directly.
**Migration**: None. `feed_events` is dropped in the second PR.
