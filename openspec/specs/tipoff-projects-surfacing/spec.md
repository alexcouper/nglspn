## Purpose

Surface community tip-off projects on the Discover page and project detail pages, with consistent explainer copy delivered via a shared Tooltip primitive, so visitors understand what a tip-off is and how makers can claim their project.

## Requirements

### Requirement: Discover page renders a Recent Tipoffs section below Winners

The Discover page (`/projects`) SHALL render a "Recent Tipoffs" section directly below the existing "Winners" section (and above the category rows). The section SHALL fetch from `GET /api/projects/recent-tipoffs` and render the returned projects using the same card components used elsewhere on the page.

The section SHALL be hidden entirely (heading and list) unless the response contains at least three tip-off projects. No empty-state copy SHALL be rendered when the threshold is not met.

#### Scenario: Discover page with no tip-offs hides the section

- **GIVEN** the system has no approved, published tip-off projects
- **WHEN** a visitor loads `/projects`
- **THEN** the page renders Featured, New Arrivals, and Winners as before
- **AND** the "Recent Tipoffs" heading does not appear
- **AND** no empty-state copy for Recent Tipoffs is shown

#### Scenario: Discover page with one or two tip-offs hides the section

- **GIVEN** the system has fewer than three approved, published tip-off projects
- **WHEN** a visitor loads `/projects`
- **THEN** the "Recent Tipoffs" heading does not appear
- **AND** the available tip-offs are not rendered as a standalone row

#### Scenario: Discover page with three or more tip-offs shows them in the dedicated section

- **GIVEN** the system has at least three approved, published tip-off projects
- **WHEN** a visitor loads `/projects`
- **THEN** the page renders the "Recent Tipoffs" section directly below the Winners section
- **AND** every card in the section corresponds to a project with `is_community_tipoff = True`
- **AND** none of those projects appears in New Arrivals

### Requirement: Recent Tipoffs cards do not render the per-card tip-off pill

Inside the Recent Tipoffs section, project cards SHALL NOT render the `TipoffBadge` pill, regardless of card size (hero/large or smaller layouts). The section heading already conveys that all cards within it are tip-offs.

The New Arrivals section, after the exclusion described in `community-submissions`, SHALL also not render the `TipoffBadge` (no tip-off projects reach it).

#### Scenario: Hero card in Recent Tipoffs has no pill

- **GIVEN** the Recent Tipoffs section renders a hero/large card
- **WHEN** the card is inspected
- **THEN** there is no "Tipoff" or "Community Tipoff" badge on the card

#### Scenario: New Arrivals cards have no pill

- **WHEN** any New Arrivals card is rendered
- **THEN** there is no "Tipoff" badge on the card

### Requirement: A Tooltip primitive is available for hover, focus, and tap interactions

The web-ui SHALL provide a `Tooltip` component at `src/web-ui/src/components/Tooltip.tsx` that takes a trigger element (as `children`) and a content payload (string or node).

The component SHALL:

- Open on `mouseenter` and close on `mouseleave` (desktop hover).
- Toggle on click/tap (so touch users can open and dismiss it).
- Open on `focus` and close on `blur` or when the user presses Escape (keyboard accessibility).
- Close when the user clicks/taps outside the trigger or content (when open via tap).
- Set `aria-describedby` on the trigger pointing at the tooltip body when open, and render the body with `role="tooltip"`.

No third-party tooltip library SHALL be added to support this requirement.

#### Scenario: Hover opens the tooltip

- **GIVEN** a Tooltip wrapping a trigger
- **WHEN** the user hovers the trigger with a pointing device
- **THEN** the tooltip body becomes visible
- **AND** when the pointer leaves the trigger and content, the body is hidden

#### Scenario: Tap toggles the tooltip on touch

- **GIVEN** a Tooltip wrapping a trigger on a touch device
- **WHEN** the user taps the trigger
- **THEN** the tooltip body becomes visible
- **AND** tapping outside the trigger and body hides it

#### Scenario: Keyboard users can open and dismiss the tooltip

- **GIVEN** a Tooltip wrapping a focusable trigger
- **WHEN** the user focuses the trigger via keyboard
- **THEN** the tooltip body becomes visible
- **AND** pressing Escape hides it

### Requirement: Recent Tipoffs heading has a tooltip explaining tip-offs

The "Recent Tipoffs" section heading SHALL include a small "?" affordance (an icon button or equivalent) that, when interacted with, opens the standard tip-off explainer copy via the `Tooltip` primitive.

The standard tip-off explainer copy SHALL read exactly:

> "Community tip-offs are projects spotted and added by someone other than their makers. If this is your project, get in touch: alex@naglasupan.is"

The email address SHALL be sourced from a single `SITE_EMAIL` constant in `src/web-ui/src/lib/constants.ts`.

#### Scenario: Hovering the heading "?" opens the explainer

- **GIVEN** the Discover page is rendered with the Recent Tipoffs section visible
- **WHEN** a user hovers the "?" affordance next to the section heading
- **THEN** a tooltip appears containing the standard tip-off explainer copy
- **AND** the copy includes the site email address

### Requirement: Project detail page tip-off badge has the same explainer tooltip

On the project detail page banner, the existing "Community Tipoff" badge SHALL be wrapped in the `Tooltip` primitive so that hovering, tapping, or focusing the badge opens the same standard tip-off explainer copy used on the Discover section heading.

The badge's visual presentation (colour, label, position) SHALL remain unchanged from prior behaviour.

#### Scenario: Hovering the badge on the detail page opens the explainer

- **GIVEN** a tip-off project's detail page is rendered
- **WHEN** a user hovers the "Community Tipoff" badge in the banner
- **THEN** a tooltip appears containing the standard tip-off explainer copy
- **AND** the copy is identical to the copy shown on the Discover section heading

#### Scenario: Tapping the badge on touch opens the explainer

- **GIVEN** a tip-off project's detail page is rendered on a touch device
- **WHEN** a user taps the badge
- **THEN** the explainer tooltip opens

### Requirement: A site-email constant is the single source of truth for the contact email

The web-ui SHALL hold the site contact email in a single constant at `src/web-ui/src/lib/constants.ts`:

```
export const SITE_EMAIL = "alex@naglasupan.is";
```

All UI surfaces that reference the contact email — including the existing `/about/contact/page.tsx`, the tip-off explainer copy, and any future addition — SHALL read from this constant rather than hardcoding the address inline.

#### Scenario: Searching the web-ui for the literal address returns only the constant

- **WHEN** the web-ui codebase is searched for the literal string `alex@naglasupan.is`
- **THEN** the only match is the assignment in `src/web-ui/src/lib/constants.ts`
