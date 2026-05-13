# Articles, Following & News — Open Questions (v2)

Pivoted from v1 (standalone blog at blog.naglasupan.is). New shape:

- **Article** is the new primitive, lives against a Project. Authored internally on the platform OR materialised from an external RSS feed. Internal + external are equal citizens.
- **No standalone blog**. Naglasupan dogfoods: it's a Project row. Your editorial output = Articles on the Naglasupan project.
- **Follow + per-project notification settings** replace the current global `email_opt_in_*` fields.
- **Everyone auto-follows Naglasupan**, so existing email behaviour is preserved.
- `/news` has a dedicated Naglasupan section + a mixed community section. Carousel intertwines.

Sequencing (your proposal):
1. Following ability
2. Migrate global settings → per-project
3. Internal article authoring
4. Backfill Naglasupan content (non-code)
5. /news page + carousels
6. RSS ingestion → materialises Articles

---

## Carryover from v1 — answered already, no need to re-answer (just here so we don't lose them)

- Project page: carousel at bottom, "See all" expands beneath, hide-if-empty, image required, link-out in new tab.
- Profile page: same carousel component. Profile redesign deferred to its own project.
- Hero on `/news`: auto-newest, no anti-domination on the hero.
- Discover carousel: per-feed/per-project cap to avoid one source dominating.
- `/news` URL.
- RSS feed registration UX: projects can register multiple, deletable not editable, status badge each. People can register one (later phase).
- RSS approval: hybrid — feed-level approve, item-level demote. Pending shows locally only.
- Internal articles also open in a new tab when clicked — you explicitly said so. (Flagging for confirmation since it's a bit unusual.)

---

## A. Naglasupan-as-project wiring

**A1. Ownership.** The Naglasupan project is a real Project row. Who's its creator/owner?
- a) Your user account (amcouper@gmail.com).
- b) A new system user (`naglasupan-team@…`, `is_system_user=True`).
- c) Multiple owners — you and any admins you trust.

**Your answer:**
It's already a real project and behaves the same as others in that respect.

**A2. Visibility on `/projects`.** Should the Naglasupan project appear alongside community projects in category rows / discover etc., or be hidden / placed specially?

**Your answer:**
Already does

---

## B. Following — UX surface

**B1. Where does the "Follow" button live on a project page?**
- a) Prominent CTA near the title banner.
- b) In the sidebar near CreatorCredit / Tags.
- c) Inline button in an action area near Discussions.

**Your answer:**
Top bar - subtle but affordable.

**B2. What does the follow button do on first click?**
- a) Immediately follows with default channels enabled — tweak later.
- b) Opens a panel/popover where you pick channels, then confirms.
- c) Follows quietly + toast: "Following. Manage notifications →".

**Your answer:**
We'll deal with this level of detail later. But yes b) sounds good, but dismissing the panel/popover means you get the defaults set.
As part of following - in order to make current behaviour work for naglasupan project - we will need to allow "channels" to exist. There are 2 for naglasupan: competition winners
and product updates. These should have their own setting and posts should be associated with a channel (note the channel meaning is different to the next question which is more "medium")

---

## C. Notifications — channels & granularity

**C1. Channels per followed project.** Email + in-app already exist — anything else for v1? (Push, SMS — probably no.)

**Your answer:**
No

**C2. Granularity per project.** When following a project, what can a user opt into?
- a) Single switch — "Notify me about everything from this project."
- b) Per-event-type — articles (yes/no), discussions (yes/no), each with channel choice.
- c) Per-channel — email AND/OR in-app for the whole project.

**Your answer:**
Per event type - as B2 talks about. It'll be something like:
 - email only
 - in app only


**C3. Default state when auto-following Naglasupan.** Existing users currently default to opted-in for platform updates + competition results emails. For new users post-launch:
- a) All channels on for Naglasupan by default (preserves current behaviour for community).
- b) Email on, in-app off (or vice versa).
- c) All off — let them opt in.

**Your answer:**
a) all on by default.

**C4. Default state when *manually* following another project.** Same as C3 or different?

**Your answer:**
all on for now. see B2.

---

## D. Notification settings — where you manage them

**D1. Where do you go to manage per-project notifications?**
- a) Each project page has a settings panel for that project only.
- b) A global "My Followed Projects" page listing each followed project with its settings inline.
- c) Both — settings live on the project page, with a global index page that links to each.

**Your answer:**
Both - the global one is inside settings for the user.

**D2. Migration of existing global email settings.** Today's flags:
- `email_opt_in_competition_results`
- `email_opt_in_platform_updates`
- `opt_in_to_external_promotions`
- `notification_frequency` (immediate / hourly / daily / never — applies to discussion notifications)

Do these all collapse into the Naglasupan-follow channel settings? Or are some preserved as global user-level (e.g. `notification_frequency` and `opt_in_to_external_promotions` stay global, the two `email_opt_in_*` collapse)?



**Your answer:**
Yes only the email_opt_in correlate to the new project channels.

---

## E. Internal article authoring

**E1. Where does a project owner click to write a new article?**
- a) "Write article" button on the project page (visible only to owners).
- b) Project settings → "Articles" tab.
- c) Separate `/projects/<slug>/articles/new` route.

**Your answer:**
Write article on project page

**E2. Editor type.**
- a) Markdown (matches existing `long_description` / discussion bodies).
- b) Rich text WYSIWYG.

**Your answer:**
Markdown with nice previewing modes - kind of like the current emailer

**E3. Fields on an article.** Minimum: title, body, hero image. Anything else for v1? (Excerpt/teaser? Tags? Slug? Publish date control?)

**Your answer:**
Database fields? yeah this seems fine. It'll need to know which "channel" it belongs to within a project though. Also needs to know which project it belongs to.


**E4. Lifecycle.**
- Edit after publish? (yes / no)
- Delete? (hard / soft / archive)
- Drafts? (saved-as-draft state, or publish-only?)

**Your answer:**
Yes you can edit, delete after publish. You have to publish, otherwise draft only.

**E5. URL structure.**
- a) `/projects/<project-slug>/articles/<article-slug>`
- b) `/articles/<article-slug>` (project-agnostic permalink)
- c) Both, with one canonical.

**Your answer:**
When publishing, article-slug is created. Should be nested within the project or user slug URL.
This implies having a user slug which we don't.

---

## F. Approval — does it still apply, and to what?

Two kinds of articles now:
- Internal (project owner authored).
- External (materialised from RSS feed registered on the project).

**F1.** Do internal articles need approval before appearing globally, or are project owners trusted?
- a) Auto-approved — owners trusted, admins can demote individual items.
- b) Same hybrid approval as RSS — admin gate per project, individual items demote-able.

**Your answer:**
Auto-approved — owners trusted, admins can demote individual items. But there should be a flag that means we can untrust a user- ie they lose the default approved status.

**F2.** For RSS-sourced articles, confirm: hybrid still applies (feed-level approve, item-level demote, pending shows locally only)?

**Your answer:**
Feed approval stays the same yes.

---

## G. `/news` page — Naglasupan section layout

**G1. Where does the dedicated Naglasupan section sit on `/news`?**
- a) Pinned band across the top, above the hero.
- b) Distinct sidebar column on the right of the grid.
- c) Hero slot reserved for Naglasupan; community articles populate the grid below.

**Your answer:**
There will be a few larger articles - similar to how in the product page we show 3 highlighted. 1 of those 3 slots should be reserved for naglasupan. Below, a carousel shows latest
nagalsupan news - carousel style - so only the most recent few articles. And then below that is the grid of all stuff.

**G2. Visual marker on the Discover carousel.** Naglasupan items are intertwined with community ones — should they get any visual distinction (badge, border) or be visually identical?

**Your answer:**
Identical

---

## H. Profile-side articles — V1 or deferred?

Earlier you said "projects and profiles can create articles". The sequencing only mentions project-side article creation explicitly, and per-person feeds are explicitly deferred.

**H1.** For v1, is profile-side article authoring in scope, or deferred entirely?

**Your answer:**
Let's defer it but ensure that we don't do things that paint us in the corner here. It'll be a follow up.

---

## I. Anything else?

E.g. — what happens to articles when a project is rejected / icebox'd? Article comments (or does the existing project-level discussion thread serve)? Can followers see other followers? Search? Sort/filter on `/news`?

**Your answer:**
