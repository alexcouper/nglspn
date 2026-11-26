## ADDED Requirements

### Requirement: Closed highlight carries its winner

Each competition in the highlights response SHALL carry `winner`. On a closed competition with a winner, `winner` is the winning project's slug, title and a card-sized image. On every other competition it is null. The endpoint's selection and ordering are unchanged.

#### Scenario: Closed with a winner
- **GIVEN** the most recently closed competition was won by project P
- **WHEN** a client requests `GET /api/competitions/highlights`
- **THEN** that competition's `winner` carries P's slug, title and image

#### Scenario: Active competition
- **WHEN** a competition in the response is accepting applications or voting
- **THEN** its `winner` is null
