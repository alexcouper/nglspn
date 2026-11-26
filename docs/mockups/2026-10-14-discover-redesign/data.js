// Captured from api.naglasupan.is on 2026-10-14 so the options are judged
// against the content that actually exists, not filler.
//   /api/feed?limit=25            -> ARTICLES
//   /api/projects/categories      -> CATEGORIES
//   /api/projects/by-category/... -> OUTDOORS (the New arrivals rail)
//   /api/competitions/highlights  -> COMP_OPEN
const CDN = "https://cdn.naglasupan.is/projects/f44fcbf5-8737-4beb-bdaf-94a3f8c15446";

const ARTICLES = [
  { date: "2026-10-07", channel: "Reviews", title: "Project Review: Næsta stig",
    summary: "Take your child's maths to the next level",
    img: CDN + "/ed5792c040f8/heimur.png" },
  { date: "2026-10-02", channel: "Competition Winners", title: "Leiðarvísir wins Naglasúpan #10",
    summary: "Congratulations to Magnús Atli Gylfason who has won the closest of contests with the trip planning app Leiðarvísir!",
    img: CDN + "/8185dfabf701/sveppur-result.jpg" },
  { date: "2026-09-27", channel: "Competition Winners", title: "Pick the Sveppur winner — voting open until Friday @ kl 12",
    summary: "The Sveppur competition has closed — it's ranking time",
    img: CDN + "/19a0e4b65dcc/sveppur-wide.jpg", stale: true },
  { date: "2026-09-19", channel: "Reviews", title: "Project Review: Proto.is",
    summary: "Got an idea you've never quite got round to starting? The free 4 week course from Proto.is may be just the thing",
    img: CDN + "/4ceaa7003831/Screenshot2026-09-19at15.03.50.png" },
  { date: "2026-09-16", channel: "Reviews", title: "Project Review: Gulrot.is",
    summary: "Every child has things they could do with a bit of encouragement in. Gulrót is here to help.",
    img: CDN + "/164121b39c36/large1.webp" },
  { date: "2026-09-04", channel: "Reviews", title: "Project Review: Atlas",
    summary: "Jan Hinrik Hansen's Atlas is here to help us get to know the world in which we live",
    img: CDN + "/94573c29f9a3/thumb.webp" },
  { date: "2026-09-04", channel: "Updates", title: "New categories",
    summary: "We've reached 70 projects submitted since the start of the year — the number and variety means again we need to revisit the categorisation of projects.",
    img: CDN + "/f1dcb72488b1/00-overview.png" },
  { date: "2026-08-30", channel: "Competition Winners", title: "Spínat: Competition #9 Results",
    summary: "Voting for Naglasúpan #9 — Spínat finished today, and the community has ranked a winner from the four projects.",
    img: CDN + "/8db3dae28b74/spinat-result-rpc.jpg" },
  { date: "2026-08-20", channel: "Updates", title: "Voting Changes — Schulze",
    summary: "The ranking-projects page suffered from a couple of biases that have led to a complete revamp.",
    img: CDN + "/f210615e4f4e/gemini-image-2_Bright_outdoor_scene_on_a_sunlit_lawn_a_pale_wooden_ballot_box_with_a_slot_on_a_-3.jpg" },
];

const REVIEWS = ARTICLES.filter((a) => a.channel === "Reviews");

const CATEGORIES = [
  { name: "Developer Tools", slug: "developer-tools", count: 11 },
  { name: "Productivity & Business", slug: "productivity-business", count: 11 },
  { name: "Community & Public Good", slug: "community-public-good", count: 15 },
  { name: "Cost of Living", slug: "cost-of-living", count: 7 },
  { name: "Games & Puzzles", slug: "games-puzzles", count: 6 },
  { name: "Events & Gatherings", slug: "events-gatherings", count: 4 },
  { name: "Family & Wellbeing", slug: "family-wellbeing", count: 10 },
  { name: "Outdoors & Hobbies", slug: "outdoors-hobbies", count: 10 },
  { name: "Icelandic Language", slug: "icelandic-language", count: 4 },
];

const P = (id, hash, path) =>
  `https://cdn.naglasupan.is/projects/${id}/${hash}/${path}`;

// Outdoors & Hobbies, sort=newest. 10 projects, 3 competition winners,
// 3 with no tagline at all. `added` is illustrative: the discover payload does
// not currently carry an arrival date.
const OUTDOORS = [
  { title: "Ljósin á ströndinni", tagline: "Gagnvirkt kort af vitum og ljósduflum Íslands, með hreyfanlegum ljósmerkjum, lituðum geirum og drægni.",
    icon: P("545f8864-14e4-48b7-ba98-5f9d8a47c097","d08befe1206b","ljosin-a-strondinni-naglasupan/thumb.webp"),
    shot: P("545f8864-14e4-48b7-ba98-5f9d8a47c097","d08befe1206b","ljosin-a-strondinni-naglasupan/medium.webp"),
    wins: [], added: "5 Oct" },
  { title: "Hlaupaplan.app", tagline: "Hlaupaplan á þínum forsendum",
    icon: P("20e41722-d722-47d7-a9c0-166e8f1261bc","ec998955b0ee","icon/thumb.webp"),
    shot: P("20e41722-d722-47d7-a9c0-166e8f1261bc","f515bd07f957","hlaupaplan_2/medium.webp"),
    wins: [], added: "26 Sep" },
  { title: "folfvellir.is", tagline: "Interactive map of every disc golf course in Iceland",
    icon: P("6eb5b6d7-05b1-46b3-bebe-42d1ca8cd4e7","3f6311fb882a","Folfvellirlogo/thumb.webp"),
    shot: P("6eb5b6d7-05b1-46b3-bebe-42d1ca8cd4e7","acd500c7e493","folfvellir.is/medium.webp"),
    wins: [], added: "14 Sep" },
  { title: "WikiRadar", tagline: "Get Wikipedia articles based on your location and navigate to them",
    icon: P("159b0947-2390-4ae2-b7b9-bd44c3dc5f85","3a00e724804e","banner/thumb.webp"),
    shot: P("159b0947-2390-4ae2-b7b9-bd44c3dc5f85","3a00e724804e","banner.png"),
    wins: [], added: "30 Aug" },
  { title: "yarnpalette.xyz", tagline: "Find your perfect yarn match instantly!",
    icon: P("99545056-fbe6-448f-8bae-62c1534fc4a2","147bf18f2b03","yarnpalette.png"),
    shot: P("99545056-fbe6-448f-8bae-62c1534fc4a2","d14bce4187d8","yarnpalette.png"),
    wins: ["Næpa"], added: "2 Jul" },
  { title: "Navoa", tagline: "Coastal Cruising Tracking System",
    icon: P("9ff7c07a-47ef-47c9-9cba-916d0b8baa87","220912a623e7","navoa_play_store_512/thumb.webp"),
    shot: P("9ff7c07a-47ef-47c9-9cba-916d0b8baa87","073441063d8a","iphone_tracking_homescreen/medium.webp"),
    wins: [], added: "19 Jun" },
  { title: "beadblueprint.uk", tagline: "Free and ad free bead pattern library and design tool",
    icon: P("c8d64e68-5f07-46d1-b4dc-65d4ba2f2eaa","32f3ad21bc2c","ScreenShot2026-05-11at10.09.42/thumb.webp"),
    shot: P("c8d64e68-5f07-46d1-b4dc-65d4ba2f2eaa","e96d4913a55c","ScreenShot2026-05-11at10.09.42/medium.webp"),
    wins: [], added: "11 May" },
  { title: "sundlaugar.com", tagline: "",
    icon: P("fb56e658-5815-48e3-9711-b054a6d6544e","5326e3b2acaf","IMG_5897/thumb.webp"),
    shot: P("fb56e658-5815-48e3-9711-b054a6d6544e","5326e3b2acaf","IMG_5897/medium.webp"),
    wins: [], added: "8 Apr" },
  { title: "rastimar.golf.is", tagline: "",
    icon: P("1beac070-fc4e-46c0-91e5-57744b6167bc","7f3221e40377","Screenshot2026-02-08at14.20.07/thumb.webp"),
    shot: P("1beac070-fc4e-46c0-91e5-57744b6167bc","7f3221e40377","Screenshot2026-02-08at14.20.07/medium.webp"),
    wins: ["Gulrót"], added: "8 Feb" },
  { title: "morphvox.net", tagline: "",
    icon: P("898b8389-9afd-4786-ace5-2d99e6899c74","313c1c7241b8","10/thumb.webp"),
    shot: P("898b8389-9afd-4786-ace5-2d99e6899c74","313c1c7241b8","10/medium.webp"),
    wins: ["Laukur"], added: "17 Jan" },
];

// GET /api/competitions/highlights, 2026-10-14. Every open competition, then the most
// recently closed one; the page takes the first.
const COMP_OPEN = {
  name: "Tómatur", slug: "tomatur", status: "accepting_applications",
  submission_deadline: "2026-10-25", voting_end_date: "2026-10-28",
  prize: "50.000 ISK", entries: 2, daysLeft: 11,
  image: "https://cdn.naglasupan.is/competitions/3ad2ae4b-8770-4490-869c-005fbc680300/tomatur-square.jpg",
};
