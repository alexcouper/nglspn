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

Adds the Follow primitive and the "Follow this project" UX. No notifications wired up yet (Phase 2 does that).

### UX

- **Follow button** in the project page's top bar — subtle but visible. Label: "Follow" (unfollowed) / "Following" (followed).
- **First-click behaviour**: opens a small popover listing channels × mediums with all switches defaulting on. Two actions: "Save" (commit the follow with these settings) or dismissing the popover (commits the follow with defaults). Either way, you're now following.
- **Subsequent clicks**: opens the same popover; "Unfollow" lives at the bottom.
- The exact visual/interaction detail of the popover is deferred — design pass will happen in phase 2 when settings are first wired up.

### Auto-follow Naglasúpan

- On user creation: a Follow row is created against the Naglasúpan Project with all channels × mediums set to on.
- Backfill migration creates Follow rows for every existing user, also all on. (See migration semantics in Phase 2.)

### Behaviour

- Following is permitted whether or not the project is approved/featured/etc. — same visibility rules as today's project pages.
- Unfollow deletes the Follow row (and its per-channel preferences).
- No "followers count" visible anywhere in v1. Not exposed to project owners either. Keeps follow private until we decide the social model.

---

## Phase 2 — Per-project notification settings & migration

Migrates today's user-global email flags into per-Follow channel preferences, and adds the UI to manage them.

### Settings location

Two places — both required:

- **On the project page**, via the Follow popover (see Phase 1). Same popover, more polished now: clear list of channels with email + in-app toggles per channel.
- **Global "My followed projects" page**, accessed from user settings (existing settings nav). Lists every Project the user follows with each project's channel preferences inline (collapsed by default; click to expand).

### Migration of existing global flags

Today's User fields and what happens to each:

| Field | Fate |
|---|---|
| `email_opt_in_competition_results` | Maps to Naglasúpan → "Competition Winners" channel → email switch. |
| `email_opt_in_platform_updates` | Maps to Naglasúpan → "Product Updates" channel → email switch. |
| `notification_frequency` | Stays as user-global. Governs discussion-notification cadence (existing behaviour). |
| `opt_in_to_external_promotions` | Stays as user-global. Unrelated to channels. |

In-app switches default on for migrated users (they didn't have a control before; on is the closer-to-current behaviour for an existing in-app notification system).

The migration is a one-shot data migration that runs on phase-2 deploy. After it runs, the two `email_opt_in_*` fields are removed (or left in place and ignored — pick at implementation time, doesn't affect the design).

### What Phase 2 changes vs. what it leaves alone

- Phase 2 builds the per-channel Follow data, the migration, and the settings UI to manage it.
- Phase 2 does **not** yet flip the outbound email send path — that happens in Phase 3, when articles can actually be published. Between Phase 2 and Phase 3, the legacy email pipeline keeps reading `email_opt_in_*` (which are kept in sync with the new per-channel switches during the transition, or unchanged because nothing yet writes to them through the new UI — implementation choice).
- The cutover is "no-regression" because by the time Phase 4 backfills content, the new send path is live (Phase 3) and seeded migration values match what users had before.

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
- **Publish**: explicit action. Sets `published_at`, creates the slug, fires notifications (Phase 5 wires those).
- **Edit after publish**: allowed. Body/title/hero/channel all editable. No "edited" badge on the article — owner is trusted with their own content. Approval state doesn't reset on edit.
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

Notification firing is wired up in this phase, because Phase 4's backfill is meant to "result in users getting them — same experience as today". When an Article is published (and approved, if applicable):

- For each User who Follows the Project: look up their preference for this Article's Channel.
  - If email switch on → enqueue email (subject to existing email rate-limit / cadence — `notification_frequency` continues to govern, applied at user-global level).
  - If in-app switch on → create an in-app notification.

The in-app notification surface extension (so existing `Notification` model can point at an Article in addition to a Discussion) is part of this phase. See **Notes on existing models** below for options.

The article-publish path is also where the **outbound email send path is flipped over** to consult per-channel Follow preferences instead of the legacy `email_opt_in_*` flags. The legacy fields are no longer read after this phase.

---

## Phase 4 — Backfill Naglasúpan content (not code)

Content op, no engineering. The point is to validate that the user-facing experience is unchanged before flipping the send-path over.

Steps:
- Create the Naglasúpan Project row if it doesn't already exist (already exists, per A1).
- Confirm the two channels exist: "Competition Winners", "Product Updates".
- Write internal Articles for the recent product updates and competition results that historically went out by email. Each one assigned to the appropriate channel.
- Soft-launch by toggling the email send path to read from the Naglasúpan Follow → channel switches (Phase 2's outbound change). At this point existing users continue to receive emails because they were migrated to "all on".

Acceptance: an existing subscriber's inbox experience matches the pre-deploy experience, and the same content is also viewable on the project page and at `/news`.

---

## Phase 5 — `/news` page and on-platform rendering of articles

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
- **Naglasúpan is already a Project row** (per your A1/A2 answers). No special-casing in the model; the only special-casing is the auto-follow on user creation and the reserved highlight slot on `/news`.

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
5. **Migration write order** — when seeding Follow rows for existing users during the Phase 2 migration, the migration runs before Phase 4 content backfill. Existing users will briefly have empty Naglasúpan article history but their Follow row already exists, so the next published Article fires normally.

---

## Roadmap mapping

The six phases above are independent enough to be planned and shipped in sequence with no big-bang. Each phase is a candidate for its own implementation plan.

- **Phase 1 (Following)** — pure additive, no user-visible change to existing flows until Phase 2.
- **Phase 2 (Settings migration data + UI)** — builds the per-channel preference store and the management UI. Doesn't flip the outbound send path yet.
- **Phase 3 (Internal authoring + notification firing)** — adds Article publishing and ties it to the new per-channel notification path. This is where the outbound email path actually switches over. Highest-risk phase for existing-user experience.
- **Phase 4 (Content backfill)** — content op, no code. Validates no-regression.
- **Phase 5 (`/news` + carousels)** — additive UI only; no behaviour changes elsewhere.
- **Phase 6 (RSS ingestion)** — additive; needs admin queue work.

Phases 5 and 6 are independent of each other and could be parallelised if there are two implementers. Everything depends on 1 → 2 → 3 in that order.
