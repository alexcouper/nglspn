# Community guides: English and Icelandic

Naglasúpan’s guides connect discovery to participation: trying a project,
sharing work, giving feedback, or contributing. Success means more useful
community activity, not sales leads. The content strategy groups practical
questions into connected hub pages and supporting guides.

## Audience and evidence

The initial audience is people building software in Iceland, people learning
to contribute, and people looking for locally made tools. Both English and
Icelandic are included at the owner’s request. The rest of the application
retains its existing language; Icelandic instructions quote English UI labels
where needed to help readers find the right control.

The project README, `/about/why`, and existing application flows establish the
scope. A public search on 2026-09-29 surfaced Naglasúpan’s project pages and
[Northstack’s description of its community work](https://www.northstack.is/about/).
The opportunity hypothesis is practical participation guidance adjacent to the
project directory, while Northstack provides a broader startup perspective.
This is not a measured competitor traffic or content-gap analysis.

No Search Console export, keyword-volume data, visitor interviews, or support
transcripts were available. The query targets below are editorial hypotheses,
not verified search volume or difficulty scores. Priorities reflect fit with
the platform and usefulness to a visitor. Do not describe the guides as
research findings or promise a ranking or AI citation increase.

## Pillars and initial topics

Each pillar has an overview and two distinct supporting guides. All pages
are informational and searchable; templates and checklists also give people
something worth sharing. English URL slugs remain stable in both languages.

| Priority | Page under `/guides/` | Query intent / participation stage | Role and rationale |
| --- | --- | --- | --- |
| 1 | `iceland-developer-community` | Iceland developer community / discover | Hub: explains the community through its projects |
| 1 | `iceland-developer-community/find-projects` | Icelandic software projects / explore | Spoke: connects local discovery to the directory and a real example |
| 2 | `iceland-developer-community/get-involved` | join developer community Iceland / participate | Spoke: a practical introduction for someone without a project |
| 1 | `share-a-side-project` | how to share a side project / share | Hub: explains the actual draft, review, and competition distinctions |
| 1 | `share-a-side-project/project-page-checklist` | side project description template / prepare | Spoke: reusable structure plus publishing checks |
| 1 | `share-a-side-project/get-useful-feedback` | get feedback on side project / improve | Spoke: request template and observation log |
| 2 | `contribute-to-projects` | contribute to software projects / contribute | Hub: code and non-code paths, with permission and scope made clear |
| 2 | `contribute-to-projects/first-contribution` | first software contribution checklist / act | Spoke: a manageable task and review handoff |
| 2 | `contribute-to-projects/find-collaborators` | find side project collaborators / collaborate | Spoke: reusable collaboration brief |

Icelandic intent includes “hugbúnaðarverkefni á Íslandi”, “deila hliðarverkefni”,
“endurgjöf á verkefni”, and “finna samstarfsfólk”. These are starting hypotheses
to refine using actual search queries, not literal keyword-density targets.

```text
/guides                       /is/guides
  ├─ iceland-developer-community
  │    ├─ find-projects
  │    └─ get-involved
  ├─ share-a-side-project
  │    ├─ project-page-checklist
  │    └─ get-useful-feedback
  └─ contribute-to-projects
       ├─ first-contribution
       └─ find-collaborators
```

Each language has the full tree. Indexes link to every hub and spoke; hubs
link to their spokes; breadcrumbs link back to parents; contextual and related
links connect tasks across pillars. Each guide has a switch to its exact
counterpart. Participation links point to existing public or authenticated
application routes. The project directory remains the home destination.

## Search and AI discovery

All guide content is rendered at build time and visible in HTML without
client JavaScript. The empty page-wide Suspense boundary has moved to the
project, login, registration, onboarding, and email-verification layouts that
need it for query-string hooks. Reading pages can now arrive visibly rather than in a
hidden streaming container that requires JavaScript to reveal. Navigation
hydrates with its authentication provider rather than inside a separate
boundary, avoiding a race with the initial sign-in-state update. Each page has
a unique localized title and description,
self-canonical, reciprocal `en`/`is`/`x-default` alternates, social metadata,
visible update date, and matching structured data. Hubs use `CollectionPage`
with `ItemList`; spokes use `Article`; both include breadcrumbs. The language
of each guide is set on its main content region; the existing global shell
is still English.

The sitemap includes both language variants of every guide and existing
public static destinations. It does not enumerate dynamic projects or
articles; a future extension needs a reliable feed of approved, public URLs.
`robots.txt` advertises the sitemap and preserves open crawling.

This follows [Google’s guidance for generative AI search](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide):
useful original value, accessible content, and sound technical SEO. There is
no special schema required for AI visibility and no guaranteed inclusion.
We do not add fabricated statistics, ratings, reviews, authors, or FAQ rich
result claims. Examples are identified; external claims link to their source.

## Editorial maintenance and distribution

Source content lives in `src/web-ui/src/content/guides.ts` and `guides-is.ts`.
The Icelandic file translates the complete articles while sharing identities,
anchors, relationships, and substantive update dates. Keep both versions in
sync when behavior changes. The tests catch broken guide links, orphaned
topics, missing sections, metadata inconsistencies, and sitemap omissions.

Have an Icelandic-speaking editor review phrasing before release. Recheck
platform instructions whenever publishing, following, or competition entry
changes. Review links and examples quarterly. Change the visible update date
only when the content itself changes meaningfully, never on each build.

Suggested next six editorial slots: four searchable pieces or improvements
based on actual queries, one creator interview or permission-based case study,
and one experiment such as a downloadable project brief. Start with evidence
from the community before choosing more topics; do not generate pages for
minor variations of the same search phrase.

For each pillar, prepare one useful excerpt for the community and one brief
for an appropriate community partner. Reuse the template or checklist in those
excerpts and link to the canonical guide. Ask contributors before publishing
their stories or private feedback. No messages have been sent as part of
this implementation.

## Measurement after deployment

### Brand searches and Icelandic discovery

The community hub also answers “What is Naglasúpan?” / “Hvað er Naglasúpan?”.
It explains the nail-soup story from the project’s README, includes the requested
“nagla súpa” phrase once in a visible section heading in each language, and
connects the name to software projects and participation in Iceland. The
existing URL and its language counterpart stay unchanged. The About page links
to the story in both languages, and the project directory has an explicit
brand-and-Iceland title and description.

A search check on 2026-09-29 found mixed intent for “nagla súpa” and “naglasúpa”,
including geographic names, soup content, and a separate Icelandic business.
These were general web results, not a geolocated Google Iceland rank report.
Treat the spaced query as a secondary brand-discovery hypothesis. Prioritize
the correct brand name “Naglasúpan” alongside “hugbúnaðarsamfélag á Íslandi”
and “íslensk hliðarverkefni”; no search-volume or ranking claim is implied.

This is Iceland-focused organic discovery. The content does not establish a
physical visitor location or a local-business listing. Track branded queries
separately from topic queries, filter Search Console performance to Iceland,
and compare English and Icelandic landing pages after indexing. Measure
qualified visits and onward project discovery, rather than unrelated soup traffic.

### Launch checks

1. Submit `/sitemap.xml` to Search Console and inspect one hub and one spoke
   in each language for indexing and canonical selection.
2. Establish a baseline for organic landing visits by guide and language,
   query impressions, clicks, and referrals from AI services where visible.
3. Review onward visits to projects and actual participation: follows,
   submitted projects, discussions, and useful contributions. These are
   proposed measures; this change does not instrument new analytics events.
4. At 30, 60, and 90 days, compare results, improve pages answering real
   queries, and use community questions to select the next topic. Record
   manual AI citation checks as observations, not stable rankings.

Indexing and visibility depend on deployment and external search systems.
The implementation supplies content and discovery infrastructure; it cannot
establish traffic or citation gains before release and measurement.
