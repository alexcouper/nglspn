import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import {
  fetchCategories,
  fetchCompetitionHighlights,
  fetchNewArrivals,
  fetchRecentArticles,
  fetchRecentTipoffs,
  fetchSpotlightArticles,
  fetchWinners,
} from "@/lib/api/server";
import { ProjectsPage } from "./ProjectsPage";
import { SITE_URL } from "@/lib/constants";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("projects.listing");
  const title = t("metaTitle");
  const description = t("metaDescription");
  return {
    title,
    description,
    alternates: { canonical: `${SITE_URL}/projects` },
    openGraph: {
      type: "website",
      title,
      description,
      url: `${SITE_URL}/projects`,
      siteName: "Naglasúpan",
      images: [{ url: "/icons/app/logo.png", alt: "Naglasúpan" }],
    },
    twitter: {
      card: "summary",
      title,
      description,
      images: ["/icons/app/logo.png"],
    },
  };
}

export default async function PreviewProjectsPage() {
  // The front-page reads fail on their own: null hides the part they feed.
  const [
    categories,
    newArrivals,
    recentTipoffs,
    winners,
    recentArticles,
    spotlightArticles,
    highlights,
  ] = await Promise.all([
    fetchCategories(),
    fetchNewArrivals(),
    fetchRecentTipoffs(),
    fetchWinners(),
    fetchRecentArticles().catch(() => null),
    fetchSpotlightArticles().catch(() => null),
    fetchCompetitionHighlights().catch(() => null),
  ]);

  return (
    <main className="min-h-screen bg-muted pt-14">
      <ProjectsPage
        initialCategories={categories}
        initialRecentArticles={recentArticles}
        initialSpotlightArticles={spotlightArticles}
        initialCompetitions={highlights?.competitions ?? null}
        today={new Date()}
        initialNewArrivals={newArrivals}
        initialRecentTipoffs={recentTipoffs}
        initialWinners={winners}
      />
    </main>
  );
}
