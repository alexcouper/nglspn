# Design: refine competition entry surfaces

## Context

See [`proposal.md`](proposal.md) for what is wrong. The base change,
[`add-explicit-competition-entry`](../add-explicit-competition-entry/design.md),
is not revisited here — its model, rules and endpoint stand. This change is
entirely about presentation, plus one admin gap and one field on a response
schema.

Four existing facts shape it:

- **There is a `Dialog` component** (`src/web-ui/src/components/Dialog.tsx`)
  wrapping the native `<dialog>` element, with backdrop, ESC routed through
  `onClose` and click-outside handling. `EnterCompetitionDialog` predates
  nothing — it simply did not use it.
- **`ChannelToggleList` is the precedent for a shared row list.** It renders the
  per-channel checkboxes for both the follow popover and the following page,
  "so the two can't drift apart", and takes only `channels` and `onToggle`. The
  same shape solves the two entry dialogs.
- **`NotificationProjectIcon` is already generic.** Its props are
  `imageUrl`/`title`/`size`; it renders the image or a palette-picked initial.
  Nothing in it knows about notifications.
- **`CompetitionReveal` is already a client component** with `useAuth`, so a
  dialog on the competition page costs no new boundary.

## Goals / Non-Goals

**Goals:**

- Entry is offered without leaving the page the user is on.
- A route's name says what the page does.
- The two entry dialogs look like each other and like the rest of the app.
- A project's standing has one home.
- Staff can see and edit a competition's entries from either side.

**Non-Goals:**

- Changing who may enter what, or how that is decided.
- Threading competition context through project creation.
- A general dialog-footer or dialog-list abstraction beyond what these two
  dialogs need.

## Decisions

### What is shared, and what is two copies

The user-visible requirement is that the two dialogs look alike. The
implementation requirement is that neither becomes the other's configuration.
The line falls here:

**Shared:**

- `Dialog` — the shell. Both dialogs pass `labelledBy` and their own heading.
- **`ChoiceList`** (new) — the selectable rows:

  ```tsx
  interface Choice {
    id: string;
    title: string;
    subtitle?: string;
    imageUrl?: string | null;
  }

  interface ChoiceListProps {
    name: string;              // radio group name
    choices: Choice[];
    selectedId: string | null;
    onSelect: (id: string) => void;
  }
  ```

  It knows nothing about competitions, projects, deadlines or eligibility. Each
  dialog maps its own data into `Choice[]` — one `.map()` each, and the two maps
  are the only place a competition or a project is mentioned. A single choice
  renders as a plain row with no radio: with nothing to choose between, a radio
  is a control that cannot be operated.

- **`EntityIcon`** — `NotificationProjectIcon` renamed, unchanged otherwise.
  `ChoiceList` uses it for `imageUrl`. Importing a component called
  `NotificationProjectIcon` into a competition dialog is exactly the misleading
  coupling worth avoiding, and the rename is two files: the component and
  `NotificationGroupItem.tsx:42`.

- `formatDate`, `describeApiError`, `btn-primary` / `btn-secondary` — as
  everywhere else.

**Not shared — two components:**

`EnterCompetitionDialog` (post-publish, a project choosing a round) and
`EnterProjectDialog` (competition page, a round choosing a project) differ in
their heading, their subtitle, their footer labels, their empty state, what
varies in the list, what happens on success, and where the data comes from —
one is handed opportunities it already has, the other fetches
`GET /api/my-projects` when it opens. Merging them means a props union with a
`mode` discriminator, which is a configuration object wearing a component's
clothes: every future change to one has to prove it does not break the other.
Two ~70-line components over a shared `Dialog` and a shared `ChoiceList` is less
code than the parameterised one and reads without a decoder.

Rejected: extracting a `DialogActions` footer. Seven dialogs write
`<div className="flex gap-2 justify-end">` inline today. Extracting it is
defensible and is a separate, repo-wide change; doing it for two of the seven
leaves the codebase with two conventions instead of one.

### The dialogs select, then confirm

Both dialogs put one primary action in the footer rather than a button per row.
With one round open — the common case, and the case in the screenshot that
prompted this — a footer pair is the only way **Enter** and **Not now** can be
aligned at all: a row-level button sits in the list, and the dismissal cannot
join it there without becoming a list item.

The first choice is pre-selected, so the common case stays one click. **Not now**
is immediately beside **Enter**, so a pre-selection is an offer rather than a
nudge — nothing is entered without pressing **Enter**.

### A draft is ineligible, decided on the server

Found by driving the running app: the competition chooser listed a `DRAFT`
project, and pressing **Enter** returned `400` — *"A draft must be published
before it can enter a competition."* The project page's Settings tab had the
same fault, three controls deep.

The base change made this reachable on purpose. `_opportunity` did not consider
`DRAFT`, and `enter_competition` rejected it separately, on the reasoning that
"the post-publish dialog needs the answer computed before the project is
published". That reasoning does not match the code: `ProjectDetail.handlePublish`
reads `competition_standing` off the **publish response**, so the project is
already `PENDING` when the dialog is built. With the chooser and the cards strip
deleted by this change, nothing reads a draft's opportunities at all.

So the rule moves to where every other eligibility rule already lives:

```python
elif project.status == ProjectStatus.DRAFT:
    reason, blocking = IneligibleReason.PROJECT_DRAFT, None
```

placed after the `REJECTED`/`ICE_BOX` rule and before the series check, so a
tipoff still outranks it and a draft is not told which series blocks it.

A distinct `project_draft` rather than folding into `project_status`: the two
want different sentences. A draft is one publish away — *"Publish this project
before it can enter a competition"* — where `project_status` means rejected or
iced, which no action of the contributor's fixes.

The client-side alternative — each surface filtering drafts itself — was
rejected for the reason the base design gives for putting eligibility on the
server at all: it duplicates the rule in TypeScript, and the drift surfaces as a
button that 400s. Which is precisely the bug being fixed.

The endpoint keeps its own `DRAFT` check, which runs before the opportunity
lookup and so keeps producing the specific message rather than the generic
"cannot enter that competition".

### `/create` replaces `/submit` outright, with no redirect

`/submit` has no external referrer in this repo — the only links are the four
in-app CTAs being repointed, plus a passing mention in
`openspec/specs/community-suggestions-ui/spec.md:11` that says "if present". A
redirect would exist to serve traffic there is no evidence of, and would keep a
name whose whole problem is that it describes an intent the page cannot fulfil.

`/create` holds exactly what `/submit`'s lower half holds today: the URL field,
the Mine/Tipoff radios, **Create Draft**. The tipoff option is fine here —
creating a tipoff is a real thing to want. It was only wrong as the destination
of **Submit a Project** on a competition.

### The competition CTA opens a dialog rather than navigating

The user is on the competition. Sending them to another page to pick a project
and then bringing them back is two navigations to accomplish one POST. The
dialog fetches `GET /api/my-projects` when it opens, not on page load, so the
competition page's first paint is unchanged for the many visitors who never
press the button.

It filters to projects holding an eligible opportunity **for this competition**,
which the standing already answers. No new endpoint, and the filter is the same
one `EligibleProjectChooser` performed — that logic moves, it is not rewritten.

The empty state distinguishes two cases, because they need different next steps:
a user with no projects at all is told so; a user whose projects are all blocked
is told that anything already in this run of competitions cannot enter again.
Both are offered **Create a project**, with the note that publishing will offer
this round. That is honest: the round is only offered later if it is still open,
and saying "you'll be offered this round when you publish" is the same promise
the publish dialog keeps.

Anonymous users keep a link rather than a dialog. `/create` is behind
`useRequireAuth`, so the link lands them at login and back — the existing
behaviour, and a dialog that can only say "sign in first" is worse than a link
that signs them in.

### Competitions live in the Settings tab

`EditProjectContent` already owns the tabs (`Description`, `Articles`,
`Settings`) via `ProjectPageLayout`. Competitions is settings-shaped: it is
about the project's administration rather than its content. It goes into the
existing Settings tab under status and submission date rather than becoming a
fourth tab — a tab holding one section that is often a single line ("No round is
currently open") is a tab that mostly disappoints.

`ProjectCompetitions` drops its own `<section className="bg-white border
border-border rounded-xl p-5 sm:p-6">` wrapper and its `<h2>`. Inside a tab
panel that chrome nests a card in a card. What is left is the standing rendering
itself, which is the part worth keeping.

Standing and the enter handler are threaded from `ProjectDetail` through
`EditProjectContent` as props. That is three more props on a component that
already takes fourteen — worth noting, not worth a context for.

The consequence: competitions are visible in edit mode only. Preview mode
renders `ProjectDetailContent`, the public view, where `competition_standing` is
null by design. That is the right split — preview exists to show what visitors
see, and visitors do not see this.

### `/my-projects` keeps fetching standing it no longer renders

`CompetitionSummaryLine` goes, but `with_competition_standing` stays on the list
endpoint: `EnterProjectDialog` reads `GET /api/my-projects` and filters on
exactly that field. Removing it as dead weight would break the competition page
one commit later, so this is stated here rather than discovered there. The
query-count test the base change added
(`tasks.md:49`) keeps it honest.

### Admin gets a changelist and keeps the inline

`CompetitionEntryAdmin` mirrors `CompetitionReviewerAdmin` (`admin.py:938`),
which is the same shape of join row: `list_display` of competition, project and
the three provenance fields; `list_filter` on `competition`,
`competition__entry_series` and `entered_via`; `search_fields` across project
title and competition name; `autocomplete_fields` for competition and project.
That answers "which projects are in this round" and "which rounds is this
project in" from one page, at any size, which the inline cannot: twenty entries
is twenty select2 widgets on the competition form.

`entered_via` and `entered_by` stay readonly and are stamped `admin` /
`request.user` in `save_model`, the same rule `save_formset` applies to the
inline (`admin.py:727-751`). Provenance that can be typed is provenance that can
be wrong, and the whole point of the field is that it can be trusted.

`ProjectAdmin` gets a read-only entries inline — `extra = 0`, no add, no delete,
every field readonly. Editing a project's rounds from the project form would be
a second write path into the same rows for no gain; the changelist is one click
away and does it properly.

Rejected: a competitions column on `ProjectAdmin`'s changelist. It needs a
`prefetch_related` on every project list view to avoid an N+1, for a column read
rarely. The inline on the change form serves the same question at the point it
is asked.

### `CompetitionSummary` carries an image

`Competition.image_url` is an existing property (`models.py:444`) and
`CompetitionListItem` already exposes it. Adding `image_url: str | None` to
`CompetitionSummary` is the smallest change that lets a round render as a row
with its image, and it costs one field on a schema that already carries
`name`, `slug`, `status` and `submission_deadline` for the same reason.

The base change's rationale holds — a caller should be able to render a
competition named in a standing without a second request. An image is part of
rendering it.

## Risks / Trade-offs

- **Deleting `/submit` 404s any link outside this repo.** → No such link is
  known, the page is barely a quarter old, and its name is the defect. A
  redirect can be added in minutes if one turns up in the logs.
- **The competition dialog fetches every project the user owns** to filter a few.
  → `GET /api/my-projects` is the same call `/my-projects` makes and is already
  paged by nothing; a user with hundreds of projects is not a case this product
  has. A dedicated endpoint is the answer if it ever is.
- **Competitions become invisible in preview mode**, where the floating card was
  visible in both. → Preview's job is to show the public view. Someone looking
  for their standing in preview finds it one toggle away, in the tab named
  Settings.
- **Pre-selecting the first round nudges toward it.** → With several rounds open
  the order is the server's, not a ranking. **Not now** sits next to **Enter**,
  and nothing is written without pressing **Enter**.
- **The `EntityIcon` rename touches an unrelated file.** → One import and one
  call site in `NotificationGroupItem.tsx`. The alternative is importing
  `NotificationProjectIcon` into a competition dialog, which is worse forever.
- **Three more props on `EditProjectContent`.** → It is already a prop-heavy
  component; the standing is read-only data and one callback, and a context for
  it would be more machinery than the problem.

## Open Questions

None.
