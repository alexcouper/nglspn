## ADDED Requirements

### Requirement: Unsaved work survives an attempt to leave the authoring page

The authoring page holds the article body in the editor's memory until an explicit save, so leaving the page discards it. The authoring page SHALL warn the author before any navigation that would discard unsaved changes, and declining the warning SHALL leave the author on the page with the work intact.

The warning SHALL cover a click on any link in the document, whether or not the page owns it. In particular it SHALL cover the links rendered by the global site chrome — the header, the site logo, the user menu, the notifications bell and the footer — which the root layout renders as siblings of the page. A link SHALL NOT have to opt in to be guarded.

The warning SHALL also cover browser-level navigation away from the page — closing the tab, reloading, or replacing the URL — for which the browser's own unload dialog is the prompt.

Three exits stay unguarded, and are known gaps rather than intended behaviour. Unsaved work is lost without a warning when the author presses the browser's Back or Forward button; when they log out from the user menu, which unmounts the editor by clearing the session rather than by navigating; and when they open a notification from the toaster, which navigates in code rather than through a link. The change's proposal records why each is out of reach of the mechanisms this requirement is built on.

"Unsaved changes" SHALL mean the same comparison a save would write: the editor body plus every editable field against the article the server last returned. A page in step with the server SHALL NOT warn, and neither SHALL a click that keeps the author on the page — a control that is not a link, a link to the current path or a bare fragment, a link opened in a new tab, or a click already handled elsewhere.

Navigation that concludes the editing session at the author's own instruction SHALL NOT warn: the move to the project page after publishing the article, and the move to the project page after deleting it.

#### Scenario: Header link warns while the article is dirty
- **GIVEN** an author on the authoring page who has typed into the editor since the last save
- **WHEN** they click a header, logo, user-menu, notifications or footer link that leads off the authoring path
- **THEN** they SHALL be asked to confirm leaving without saving

#### Scenario: Declining the warning keeps the author and the work
- **GIVEN** an author who has been asked to confirm leaving
- **WHEN** they decline
- **THEN** the navigation SHALL NOT happen and the editor SHALL still hold the unsaved body and fields

#### Scenario: Accepting the warning leaves the page
- **GIVEN** an author who has been asked to confirm leaving
- **WHEN** they accept
- **THEN** the navigation SHALL proceed to the link's destination

#### Scenario: A clean page never warns
- **GIVEN** an author whose article matches what the server last returned
- **WHEN** they click any link that leaves the authoring page
- **THEN** they SHALL leave with no prompt

#### Scenario: Closing or reloading the tab while dirty warns
- **GIVEN** an author on the authoring page with unsaved changes
- **WHEN** they close the tab, reload, or navigate the browser to another URL
- **THEN** the browser SHALL present its unload confirmation before the page is discarded

#### Scenario: Publishing does not warn
- **GIVEN** an author on the authoring page
- **WHEN** they publish the article and the page moves them to the project page
- **THEN** no leave confirmation SHALL be shown

#### Scenario: Deleting does not warn
- **GIVEN** an author on the authoring page with unsaved changes
- **WHEN** they confirm the delete and the page moves them to the project page
- **THEN** no leave confirmation SHALL be shown beyond the delete confirmation itself

#### Scenario: Staying on the page does not warn
- **GIVEN** an author on the authoring page with unsaved changes
- **WHEN** they click a control that does not leave the page — a button, an editor tab, a link to the current path, a link opened in a new tab or window, a download link, or a link the browser hands to another application
- **THEN** no leave confirmation SHALL be shown
