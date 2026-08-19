import { ListingTabs } from "@/components/ListingTabs";
import { fetchCategories, fetchFeedPage } from "@/lib/api/server";

import { LatestFeed } from "./LatestFeed";

export const metadata = {
  title: "Latest",
  description: "What's happened on Naglasúpan lately.",
};

export default async function LatestPage() {
  const [categories, feed] = await Promise.all([
    fetchCategories(),
    fetchFeedPage(),
  ]);

  return (
    <main className="min-h-screen bg-muted pt-14">
      <ListingTabs categories={categories} active={{ kind: "latest" }} />

      <section className="py-8 px-4 sm:px-6">
        {/* Narrower than Discover on purpose: this is a reading column, not a
            browsing grid, and it stays one column at every width. */}
        <div className="max-w-3xl mx-auto">
          <LatestFeed
            initialEntries={feed.entries}
            initialCursor={feed.next_cursor ?? null}
            lead={feed.lead ?? null}
          />
        </div>
      </section>
    </main>
  );
}
