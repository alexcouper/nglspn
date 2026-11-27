## MODIFIED Requirements

### Requirement: Public surfaces show the author where they showed the project

Wherever an article is listed with its project — the public profile list, a front-page card, a "read next" card, a notification group, the article digest email, an article card — an author-owned article SHALL show the author's name instead, and link to the author's profile where the project article links to the project. The public profile list (`GET /api/users/{id}/articles`) SHALL include visible author-owned articles alongside visible articles on approved projects, with `project` null on the former.

#### Scenario: Profile list mixes both kinds
- **GIVEN** U with a visible article on approved project P and a visible author-owned article
- **WHEN** a visitor fetches `GET /api/users/{U.id}/articles`
- **THEN** both SHALL be returned, the project one with `project = {slug, title}` and the author-owned one with `project = null`

#### Scenario: Digest email byline
- **GIVEN** a recipient's article digest containing an author-owned article by U
- **WHEN** the digest is rendered
- **THEN** the entry's byline SHALL be U's name linking to U's profile, and the article link SHALL be its `/users/{U.id}/articles/{slug}` URL

#### Scenario: Front-page card
- **GIVEN** an author-owned article by U in Recent
- **WHEN** the Discover view renders
- **THEN** the card's flag SHALL be U's name and it SHALL link to `/users/{U.id}/articles/{slug}`
