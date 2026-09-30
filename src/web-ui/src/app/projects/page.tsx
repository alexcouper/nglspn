import type { Metadata } from "next";
import {
  fetchCategories,
  fetchFeaturedProjects,
  fetchNewArrivals,
  fetchRecentTipoffs,
  fetchWinners,
} from "@/lib/api/server";
import { ProjectsPage } from "./ProjectsPage";
import { SITE_URL } from "@/lib/constants";

const title = "Naglasúpan | Software projects in Iceland";
const description = "Discover Icelandic apps, tools, and side projects on Naglasúpan. Meet the people building them, try their work, and share feedback with the community.";

export const metadata: Metadata = {
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

export default async function PreviewProjectsPage() {
  const [categories, featured, newArrivals, recentTipoffs, winners] =
    await Promise.all([
      fetchCategories(),
      fetchFeaturedProjects(),
      fetchNewArrivals(),
      fetchRecentTipoffs(),
      fetchWinners(),
    ]);

  return (
    <main className="min-h-screen bg-muted pt-14">
      <ProjectsPage
        initialCategories={categories}
        initialFeatured={featured}
        initialNewArrivals={newArrivals}
        initialRecentTipoffs={recentTipoffs}
        initialWinners={winners}
      />
    </main>
  );
}
