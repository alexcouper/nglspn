# Articles, Following & News — Design

Date: 2026-05-13
Status: design (pre-implementation)

## Summary

Open up Naglasúpan's editorial output (today: emails sent to subscribers) to anonymous browsers of the public web, without losing the email channel. Do it by dogfooding: Naglasúpan's project is used - the things we currently email about become **Articles** on that project. Anyone visiting the site can read them; subscribers continue to receive them because they auto-follow the Naglasúpan project.

The same authoring primitives are then available to other projects — owners can write Articles directly, or register an RSS feed that materialises external posts as Articles.

## Goals

- Preserve today's email behaviour for existing users (no regression in what arrives in their inbox).
- Make platform-update / competition-result content visible to non-members on the public site.
- Let project owners publish updates about their own projects, either by writing on the platform or by pointing an RSS feed at it.
- Give visitors a discoverable home for news at `/news`, and surface news on project pages and the Discover page.
- Lay groundwork — but no UI yet — for following arbitrary projects with per-channel notification settings, generalising the current "subscribe to Naglasúpan emails" mental model.

## Non-goals (v1)

- Profile-side article authoring (deferred; depends on adding a user slug).
- Per-user RSS feeds (deferred, same dependency).
- Following users (only projects in v1).
- Channel-level discovery on `/news` (LLM-categorised tabs come in v2).
- In-platform reader view for articles. Articles open in a new tab and the destination is either an on-platform article page or the source URL of an external RSS item.

## Core concepts

Four new primitives, one new flag on an existing model. UX descriptions below; data structures named only as shorthand, not as a schema spec.

### Channel

A topic within a Project. Has a name (free-form, owner-chosen). Every Project gets one default Channel called "Updates" on creation. Naglasúpan is seeded with two: "Competition Winners" and "Product Updates", matching today's two `email_opt_in_*` flags 1:1. Owners can add more channels in project settings.

### Article

A piece of content published on a Project, in one Channel. Has a title, body (markdown), hero image, slug (generated on publish), publish state (draft / published), source (internal / external), optional external_url (for RSS-sourced items).

### Follow

A user's subscription to a Project. Owns per-channel × per-medium notification preferences. Mediums in v1: email, in-app. Defaults on first follow: all channels, all mediums on.

### Trust flag (on User)

Boolean, default true. When true, the user's authored Articles are auto-approved for global rendering. Admin can flip it to false; existing and future Articles by that user then require approval before global rendering. Local rendering (on the user's project page) is unaffected by the trust flag. Should be called something like article_trust.

### Notification preference (per Follow × Channel × Medium)

Each Follow × Channel pair carries an email switch and an in-app switch. The Follow exists even if every switch is off — that distinguishes "I unfollowed" from "I follow but want silence".

---

## Phase 1 — Following

Adds the Follow primitive, the "Follow this project" UX, and the one-shot data migration that seeds per-channel preferences for existing users from the legacy email flags. No notification firing yet (Phase 3 wires that up). No per-channel settings UI yet (Phase 2 adds that).

### UX

- **Follow button** in the project page's top bar — subtle but visible. Label: "Follow" (unfollowed) / "Following" (followed).
- **Click when not following**: instantly follows, with all channels × mediums defaulted to on. No popover, no confirmation.
- **Click when following**: instantly unfollows. No popover, no confirmation.
- Per-channel × per-medium switches are not exposed in Phase 1. The switches exist in storage (auto-follow writes them, migration seeds them), but no UI surface lets the user see or edit them until Phase 2.

### Identifying the house project

A new boolean `is_house_project` on Project, default `False`. Exactly one Project carries it: Naglasúpan. The Phase 1 data migration sets this on the existing Naglasúpan Project row. Auto-follow signals and the reserved `/news` highlight slot (Phase 5) look it up via this flag rather than a hardcoded slug or UUID.

A DB-level partial unique constraint (or a save-time guard) ensures only one Project carries the flag.

### Auto-follow Naglasúpan

- On user creation: a Follow row is created against the house project (Naglasúpan) with all channels × mediums set to on.
- **One-shot data migration** creates Follow rows for every existing user. For Naglasúpan, the per-channel email switches are seeded **from the legacy global flags** — not defaulted to on:
  - `email_opt_in_competition_results` → "Competition Winners" channel → email switch
  - `email_opt_in_platform_updates` → "Product Updates" channel → email switch
  - In-app switches default on (no prior signal to migrate from).
- The legacy `email_opt_in_*` fields stay in place on User. The outbound email pipeline continues to read them through Phase 2 — they're removed in Phase 3 when the send path flips over.

### Behaviour

- Following is permitted whether or not the project is approved/featured/etc. — same visibility rules as today's project pages.
- Unfollow hard-deletes the Follow row and its per-channel preferences.
- Re-following after an unfollow is a fresh start: defaults-on across all channels × mediums. Any prior per-channel tweaks are not preserved.
- No "followers count" visible anywhere in v1. Not exposed to project owners either. Keeps follow private until we decide the social model.

---

## Phase 2 — Per-project notification settings UI

Adds the UI to view and manage the per-channel × per-medium preferences that Phase 1 already populated. Pure UI/API work; no data migration (that landed in Phase 1).

### Settings location

Two places — both required:

- **On the project page**, via the Follow popover. Clicking the "Following" button now opens a popover with a list of channels and email + in-app toggles per channel. Unfollow lives at the bottom. (This replaces Phase 1's instant-unfollow on click.)
- **Global "My followed projects" page**, accessed from user settings (existing settings nav). Lists every Project the user follows with each project's channel preferences inline (collapsed by default; click to expand).

### User-global fields left alone

| Field | Fate |
|---|---|
| `notification_frequency` | Stays user-global. Continues to govern discussion-notification cadence. |
| `opt_in_to_external_promotions` | Stays user-global. Unrelated to channels. |

### Outbound email path

Phase 2 does **not** flip the outbound email send path — that happens in Phase 3, when articles can actually be published. Between Phase 2 and Phase 3:

- The legacy `email_opt_in_*` flags continue to drive the email pipeline.
- When the user changes a Naglasúpan channel email switch in the new UI, the corresponding legacy flag is **mirrored** so the legacy pipeline reflects the change. Mirror logic is scoped strictly: only the two named channels ("Competition Winners" → `email_opt_in_competition_results`, "Product Updates" → `email_opt_in_platform_updates`), and only on the house project. Other projects' channels have no legacy correlate.
- When the user **unfollows the house project entirely** (via the popover or the global page), both legacy flags are set to `False`. This is also a mirror: the user's intent "stop hearing from Naglasúpan" must be honoured by the legacy pipeline that still reads the flags.
- POST (create a follow) does NOT touch the legacy flags. Newly-created per-channel preferences are defaulted to all-on regardless of the user's existing legacy flag values — but the legacy pipeline keeps reading the legacy flag, so the user's email behaviour is the legacy flag's value until Phase 3 (or until the user manually toggles a switch, which mirrors).
- The legacy fields are removed in Phase 3 when the send path flips over.

The cutover is "no-regression" because Phase 1's backfill seeded preferences from the legacy flags (so the new switches reflect what users had), and Phase 2's mirror logic keeps the legacy flags in sync with user intent expressed through the new UI for the duration of the gap.

---

## Phase 3 — Internal article authoring

Adds the Article primitive and the UX for project owners to create them.

### Authoring entry point

- **"Write article" button** on the project page, visible only to users with `full_edit` on a `ProjectContributor` row for that project (existing trust check).
- Clicking opens a dedicated authoring page: `/projects/<project-slug>/articles/new`.

### Editor

Markdown body with side-by-side preview (or toggleable preview tab on mobile), modelled on the existing emailer's authoring experience. Pulls in the existing markdown rendering pipeline (already used for `long_description` and discussions).

### Article fields (authoring UI)

- **Title** (required).
- **Channel** (required, dropdown of this project's channels — at minimum "Updates", plus whatever the owner has added).
- **Hero image** (required at publish time; can save a draft without one). Uses the existing project-image upload pipeline.
- **Body** (markdown, required at publish time).

Images can be inserted into the body by dragging an image onto the window.

Slug is generated from the title on publish (Icelandic transliteration applied, matching existing project/competition slug logic).

### Lifecycle

- **Draft** state: not visible anywhere, not in notifications. Can be edited freely.
- **Publish**: explicit action. Sets `published_at` (defaults to now), creates the slug, and fires notifications **only if `published_at` is "now"** (see Backdated publish below).
- **Backdated publish**: the author may override `published_at` to a date in the past at publish time. A backdated publish does **not** fire notifications — neither email nor in-app. This is the mechanism by which Phase 4's content backfill runs without notification storms: admins enter historical articles with their original send date, silently.
- Setting `published_at` to a date in the **future** is out of scope for v1; the publish action commits immediately.
- **Edit after publish**: allowed. Body/title/hero/channel all editable. No "edited" badge on the article — owner is trusted with their own content. Approval state doesn't reset on edit. Editing `published_at` after publish is also allowed but never fires notifications retroactively.
- **Delete after publish**: allowed. Hard delete (mirrors how Discussions work today). Followers who already received notifications keep them.

### URL & rendering

- Article page: `/projects/<project-slug>/articles/<article-slug>`.
- Layout reuses the project-page header (so the article is clearly part of its project), with the article body as the main content. Hero image at the top.
- Internal articles, like external ones, **open in a new tab** when clicked from a carousel or news page — preserves the "external + internal are equals" framing.

### Channel management

Project owners manage their project's channels in project settings, under a new "Channels" section. UI is minimal: add channel, rename channel, delete channel (deleting a channel with articles in it requires reassigning those articles, surfaced as a guard).

### Approval

- Internal articles by users with `article_trust = true` are **auto-approved** — render locally and globally immediately.
- Internal articles by users with `article_trust = false` follow the same approval flow as RSS articles (Phase 6): local rendering immediately, global rendering blocked until admin approves the item.
- Admin can demote any individual article at any time, independent of the trust flag — demoted articles are removed from global rendering, retained locally.

### Notifications fire on publish

Notification firing is wired up in this phase. When an Article is published with `published_at` ≈ now (i.e. not backdated, see Lifecycle):

- For each User who Follows the Project: look up their preference for this Article's Channel.
  - If email switch on → enqueue email (subject to existing email rate-limit / cadence — `notification_frequency` continues to govern, applied at user-global level).
  - If in-app switch on → create an in-app notification.

Backdated publishes (Phase 4's mechanism) silently skip the notification fan-out. Followers find historical articles via `/news`, the project page carousel, or direct link — not via inbox or in-app notification.

The in-app notification surface extension (so existing `Notification` model can point at an Article in addition to a Discussion) is part of this phase. See **Notes on existing models** below for options.

The article-publish path is also where the **outbound email send path is flipped over** to consult per-channel Follow preferences instead of the legacy `email_opt_in_*` flags. The legacy fields are no longer read after this phase.

---

## Phase 4 — Backfill Naglasúpan content (not code)

Content op, no engineering. The point is to put recent historical Naglasúpan output (product updates, competition results) onto the platform as Articles so they're visible on `/news`, the project page carousel, and in the Discover carousel — **without re-notifying anyone about content they've already received by email**.

Steps:
- Confirm the Naglasúpan Project row exists with `is_house_project=True` (Phase 1's data migration set this).
- Confirm the two channels exist: "Competition Winners", "Product Updates".
- Write internal Articles for the recent product updates and competition results that historically went out by email. Each assigned to the appropriate channel, with `published_at` set to the original send date (in the past) so the **notification fan-out is suppressed** (see Phase 3 Lifecycle).

Acceptance: historical content is visible on the project page carousel, on `/news`, and in the Discover carousel — and **no notifications fire** for it (no in-app, no email).

The "no inbox regression for new content" property is delivered by Phase 3's send-path flip combined with Phase 1's migrated preferences — not by Phase 4. Phase 4 is purely about populating the visible-content surface.

---

## Phase 5 — `/news` page and on-platform rendering of articles

> **Superseded, 2026-08-13.** This phase never shipped. The `/news` destination
> and the Discover "Latest News" carousel are replaced by a Latest tab carrying
> a mixed event stream — see
> [2026-08-13-latest-feed-design.md](2026-08-13-latest-feed-design.md). The
> project-page and profile carousels below are unaffected.

Adds the news destinations and ties the notification system into article publishes.

### `/news` page layout

Three stacked sections, top to bottom:

1. **Top highlights** — 3 large article cards, similar in size and treatment to the existing 3-up highlights on the projects page. **One slot is reserved for the newest Naglasúpan article** (if any). The other two slots are filled with the newest community articles. If there's no Naglasúpan article, the slot collapses and community fills.
2. **Naglasúpan carousel** — a horizontally-scrolling carousel of the most recent Naglasúpan articles, matching the existing carousel style used elsewhere. Hidden if Naglasúpan has fewer than two articles (the single one is already in the highlight slot).
3. **Community grid** — all approved, non-demoted articles in reverse-chronological order. Filterable by **author** (the project the article belongs to). Pagination or infinite scroll — implementation detail.

### Discover (`/projects`) carousel

- A new "Latest News" section is added to the existing Discover page, alongside Featured / New Arrivals / Recent Tipoffs / Winners / Most Discussed.
- **Naglasúpan articles intertwine with community articles** in this carousel — no badge, no border distinction. They look identical.
- **Per-project anti-domination cap**: at most 2 articles per project in the carousel at any time. Naglasúpan plays by the same rule.
- "See all" → `/news`.

### Project page Latest News carousel

- Appears **at the bottom** of the project page (below long description, contributors, discussions, etc.).
- Same carousel component as the Discover carousel.
- Shows the most recent N (~6) articles for *this* project, across all of its channels. No channel filter in v1.
- "See all" **expands inline beneath** — no separate page, just more cards.
- Section is **hidden entirely** when the project has zero articles.

### Profile page

- Reuses the same carousel component, placed below the existing bio.
- In v1 this is only populated once profile-side articles exist (deferred) — so in practice this section is hidden for everyone in v1. The component is still implemented and wired, ready for the future.
- A profile redesign is a separate follow-up project.

### Empty states

- Project with no articles: project-page carousel section hidden, no link to articles from the page.
- `/news` with no articles at all (vanishingly unlikely once Phase 4 backfill lands): show a short text fallback.

### Image fallback

External articles (Phase 6) sometimes won't carry a usable image in the RSS payload. Internal articles require an image at publish time, so they're safe. For external items the ingestion pipeline picks, in order: `media:content` → enclosure → `og:image` of the source URL → first inline `<img>` in the entry body → a per-project default placeholder image. Items still always get rendered — never dropped.

---

## Phase 6 — RSS ingestion

Adds the ability for project owners to register external RSS feeds whose items materialise as external Articles on their project.

### Feed registration UX

- New **"News & links" section** in project settings, separate from the existing project-edit form.
- Owner adds a feed by providing: URL, label (free-form, displayed only in settings), and **channel pin** (a dropdown of this project's channels — every materialised Article from this feed lands in that channel).
- Owner can register **multiple feeds** per project.
- Each feed shows its status badge: Pending / Approved / Rejected.
- Feeds are **deletable but not editable** — to change a feed's URL or channel pin, delete and re-add.

### Admin approval (hybrid)

- New feeds start in **Pending**. Admin sees a queue (admin area) and approves or rejects.
- **Pending feeds still materialise Articles locally** — they appear on the project page carousel, but not in the Discover carousel and not on `/news`.
- Once approved, all past and future Articles from that feed flow to global rendering.
- Admin can **demote individual Articles** at any time, regardless of feed approval state.
- Admin can also revoke a feed's approval (back to Pending) — Articles already published stay where they are unless individually demoted.

### Ingestion pipeline (sketch — implementation plan will detail)

- Hourly poller iterates registered feeds.
- For each new entry, create an Article row with `source = external`, `external_url = <entry link>`, body = entry summary (markdown-converted from HTML), title = entry title, channel = the feed's pinned channel.
- Image picked using the fallback order above.
- Articles materialised from external feeds **never get a slug** (their canonical link is `external_url`); the article page itself isn't visited for external items — clicks go straight to `external_url`.

### Notifications on external Articles

External Articles fire notifications identically to internal ones — the system doesn't care about source.

---

## `/news` URL summary

| Surface | URL |
|---|---|
| News destination | `/news` |
| Article (internal) | `/projects/<project-slug>/articles/<article-slug>` |
| Article (external) | (clicks go to `external_url` directly; no on-platform page) |
| Project page (existing) | `/projects/<project-slug>` |
| Followed projects (settings) | `/profile/followed-projects` (or similar — exact path decided at implementation) |

---

## Notes on existing models

These are observations about how the design plugs into what's already there. Not a schema spec — implementation plan will work out exact migrations and field names.

- **`Notification` model** is currently anchored to a Discussion (`notifications.Notification.discussion` FK). Articles need to fire notifications too. Options for the implementation plan to pick from: (a) generalise the existing model to point at either a Discussion or an Article via a nullable FK pair, (b) add a separate `ArticleNotification` model, (c) introduce a generic notifiable polymorphism. The design accommodates any of these; choice depends on how invasive the migration of in-app notification UI ends up being.
- **`NotificationCadence`** (immediate/hourly/daily/never) is currently per-user. The migration plan keeps this user-global and uses it for both Article and Discussion notifications. Per-Follow-per-channel cadence is not in scope for v1.
- **Project slugs** already handle Icelandic transliteration — Article slugs reuse the same helper.
- **Naglasúpan is already a Project row.** Identified at runtime by a new boolean `is_house_project` on Project (default `False`). Phase 1's data migration sets the flag on the existing Naglasúpan row. A DB-level partial unique constraint (or a save-time guard) ensures only one Project carries the flag.
- **Legacy email flags** (`email_opt_in_competition_results`, `email_opt_in_platform_updates`) stay on the User model through Phases 1 and 2. Phase 1's data migration reads them to seed per-channel preferences; the legacy email pipeline keeps reading them until Phase 3 flips the send path; Phase 3 removes the fields.

---

## Out of scope (v1)

- **Profile-side article authoring** — depends on user slugs, which don't exist yet.
- **Per-user RSS feeds** — same dependency.
- **Following users** — only projects in v1.
- **Channel categorisation on `/news`** — LLM-driven categories ("AI", "Development", etc.) come in v2.
- **Followers count, follower list, social affordances** — keep follow private in v1.
- **In-platform reader view of external articles** — they open in a new tab to the source.
- **Per-channel cadence** (digest vs immediate per channel) — cadence stays user-global.
- **Comments on articles** — the existing project-level discussion thread serves this implicitly; we don't add a per-article comment thread.

---

## Open questions / flagged risks

These don't block the spec but are worth surfacing for implementation planning:

1. **Hero-slot domination on `/news`** — the newest approved Article is the hero; if one source posts in rapid bursts, they'll occupy the hero slot for that period. v1 acceptable risk; the demote-item lever is the mitigation.
2. **Channel renaming and follower preferences** — if a project owner renames a channel, follower preferences against the old channel transparently follow the rename (preferences are FK'd to the Channel row, not the name). Worth a test.
3. **Deleting a channel with articles** — design says "guard, owner reassigns articles first". Worth a confirmation UX, not just an error.
4. **External Articles and the trust flag** — the trust flag is on the *user* who authored an article. For external Articles the author isn't a user on the platform. So trust-flag logic only governs internal Articles; external Articles route via the per-feed approval state.
5. **Backfill suppression mechanism** — Phase 4 content backfill must not generate notifications. Mechanism: the author-settable `published_at` field. Articles published with `published_at` in the past skip notification fan-out (both email and in-app). This is documented behaviour, not a feature flag — it's how backdated publishes work in general.
6. **Migration write order** — Phase 1's data migration seeds Follow rows from the legacy email flags and runs before Phase 4 content backfill. Existing users will briefly have empty Naglasúpan article history but their Follow row already exists, so the next *new* published Article (Phase 3 onward, `published_at` ≈ now) fires notifications normally.
7. **House-project flag uniqueness** — `is_house_project` must be settable on exactly one Project. Enforce via DB partial unique constraint (`UNIQUE (is_house_project) WHERE is_house_project = TRUE`) or a save-time guard. Pick at implementation time.

---

## Roadmap mapping

The six phases above are independent enough to be planned and shipped in sequence with no big-bang. Each phase is a candidate for its own implementation plan.

- **Phase 1 (Following + preference data backfill)** — adds Follow + Channel storage, the Follow button UI (no switches yet), and the one-shot data migration that seeds Follow rows for existing users from the legacy email flags. Pure additive; legacy email path unchanged.
- **Phase 2 (Settings UI)** — adds the preference-management UI (popover on the project page + global "My followed projects" page). No data migration. Doesn't flip the outbound send path yet — that's Phase 3.
- **Phase 3 (Internal authoring + notification firing)** — adds Article publishing and ties it to the new per-channel notification path. This is where the outbound email path actually switches over. Highest-risk phase for existing-user experience.
- **Phase 4 (Content backfill)** — content op, no code. Validates no-regression.
- **Phase 5 (`/news` + carousels)** — additive UI only; no behaviour changes elsewhere.
- **Phase 6 (RSS ingestion)** — additive; needs admin queue work.

Phases 5 and 6 are independent of each other and could be parallelised if there are two implementers. Everything depends on 1 → 2 → 3 in that order.
