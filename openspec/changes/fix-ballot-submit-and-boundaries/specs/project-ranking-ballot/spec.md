## MODIFIED Requirements

### Requirement: Pending ballot changes are saved before submission

The client SHALL flush any pending debounced ranking save before requesting the status change to `completed`, so that a change made immediately before submitting is not lost. If that flush fails, the client SHALL NOT request the status change: the review stays editable, the reviewer is told the ranking was not saved and therefore not submitted, and Submit remains available to retry.

#### Scenario: Reorder then immediately submit

- **WHEN** a reviewer reorders their ranking and submits before the autosave interval elapses
- **THEN** the reordered ballot is persisted
- **AND** the review is marked completed

#### Scenario: The pre-submit save fails

- **WHEN** a reviewer reorders their ranking, submits before the autosave interval elapses, and the ranking write fails
- **THEN** no status change is requested and the review stays in progress
- **AND** the reviewer is told their ranking could not be saved and was not submitted
- **AND** the ranking remains editable and Submit can be retried

#### Scenario: Autosave fails without a submission

- **WHEN** a reviewer reorders their ranking and the autosave write fails
- **THEN** the reviewer is shown a save error
- **AND** the ranking remains editable

### Requirement: Ranked list and pool adapt to screen size

The ranked list and the unranked pool SHALL both be reachable at every screen size: presented side by side on wide screens and as two switchable tabs on narrow screens. The narrow-screen tabs SHALL implement the tab pattern in full — each tab identifies the panel it controls, each panel is labelled by its tab, and the tab set is navigable with the arrow keys — so that assistive technology can reach the unranked pool.

#### Scenario: Wide screen

- **WHEN** a reviewer views the competition on a wide screen
- **THEN** the ranked list and unranked pool are both visible at once

#### Scenario: Narrow screen

- **WHEN** a reviewer views the competition on a narrow screen
- **THEN** a tab control switches between the ranked list and the unranked pool
- **AND** the ranked-list tab shows how many projects are ranked

#### Scenario: Reaching the unranked pool with a screen reader

- **WHEN** a reviewer on a narrow screen moves to the unranked tab with assistive technology
- **THEN** the tab identifies the panel it controls and the panel is labelled by that tab

#### Scenario: Moving between tabs with the keyboard

- **WHEN** a reviewer has focus on one tab and presses the left or right arrow key
- **THEN** focus moves to the other tab and that tab becomes the selected one
