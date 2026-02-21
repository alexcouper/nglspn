import { CompetitionsList } from "./CompetitionsList";
import { fetchCompetitions } from "@/lib/api/server";
export const revalidate = 3600;

export default async function CompetitionsPage() {
  const data = await fetchCompetitions().catch(() => null);

  const sorted = data
    ? [...data.competitions].sort(
        (a, b) =>
          new Date(b.start_date).getTime() - new Date(a.start_date).getTime()
      )
    : null;

  return (
    <main className="min-h-screen bg-muted pt-14">
      <section className="bg-white border-b border-border py-10 px-4 sm:px-6">
        <div className="max-w-6xl mx-auto">
          <h1 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight">
            Competitions
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Community competitions and their results
          </p>
        </div>
      </section>

      <section className="py-8 px-4 sm:px-6">
        <div className="max-w-4xl mx-auto">
          <CompetitionsList
            initialCompetitions={sorted}
            initialPendingCount={data?.pending_projects_count ?? 0}
          />
        </div>
      </section>
    </main>
  );
}
