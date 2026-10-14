## ADDED Requirements

### Requirement: Article digest layout depends on batch size

The article digest email for a recipient SHALL order its articles newest first,
by `Article.published_at` falling back to the notification's `created_at`, and
SHALL choose its subject and body by the number of articles in the batch.

With one article, the subject SHALL be `<project title>: <article title>`,
except when the article's project has `is_house_project = True`, in which case
the subject SHALL be the article title alone. The body SHALL contain the whole
article rendered from its markdown, a byline naming the project, channel,
publication date and non-system author, and a link to the article page.

With two to four articles, the subject SHALL name the newest article under the
same house-project rule and count the rest (`..., and N more`). The newest
article SHALL show its body when short, otherwise an excerpt cut on a block
boundary followed by a link, and the remaining articles SHALL show title,
channel, project and plain-text excerpt.

With five or more articles, the body SHALL be the list of title, channel,
project and plain-text excerpt per article, and the subject SHALL state the
count.

Every layout SHALL carry the link to change article email frequency, and SHALL
be logged as `SentEmailType.ARTICLE_DIGEST`.

The Django admin digest preview SHALL render the same subject and layout the
sender would, for the same batch.

#### Scenario: One article from an ordinary project

- **GIVEN** user U has one unsent article notification for article A, titled
  "Næsta stig", on project P titled "Broadside" with `is_house_project = False`
- **WHEN** the article digest is sent to U
- **THEN** the subject is "Broadside: Næsta stig"
- **AND** the HTML part contains A's body rendered as HTML
- **AND** the HTML part contains a link to A's page

#### Scenario: One article from the house project

- **GIVEN** user U has one unsent article notification for article A, titled
  "Project Review: Næsta Stig", on the project with `is_house_project = True`
- **WHEN** the article digest is sent to U
- **THEN** the subject is "Project Review: Næsta Stig"

#### Scenario: Three articles lead with the newest

- **GIVEN** user U has unsent article notifications for A1, A2 and A3 where A3
  has the latest `published_at`
- **WHEN** the article digest is sent to U
- **THEN** the subject names A3 and ends ", and 2 more"
- **AND** A3 appears before A1 and A2 in the body

#### Scenario: Five articles fall back to the list

- **GIVEN** user U has five unsent article notifications
- **WHEN** the article digest is sent to U
- **THEN** the body is the list layout with five entries
- **AND** the subject states five articles

### Requirement: Article markdown rendered for email is sanitised and styled

Rendering an article body to email HTML SHALL flatten each `:::gallery` block
to its images, SHALL strip every tag and attribute outside the allowlist the
web article page uses (GitHub defaults plus `figure`, `figcaption` and `align`
on `div`, without `style` and without class names), and SHALL set inline
styles on `img`, `pre`, `code`, `blockquote`, `table`, `th` and `td`. Images
SHALL lose author-supplied `width` and `height` attributes and SHALL use the
`medium` variant URL where the article has one for that image.

#### Scenario: Author style attribute is stripped

- **GIVEN** an article body containing `<span style="position:fixed">x</span>`
- **WHEN** the body is rendered for email
- **THEN** the output contains no `position:fixed`

#### Scenario: Gallery becomes stacked images

- **GIVEN** an article body with a `:::gallery` block holding two images
- **WHEN** the body is rendered for email
- **THEN** the output contains both `<img>` tags
- **AND** the output contains no literal `:::`

#### Scenario: Body image uses the medium variant

- **GIVEN** an article body with `![](<original url of image I>)` where I has a
  `medium` variant
- **WHEN** the body is rendered for email
- **THEN** the `<img src>` is the medium variant's URL
