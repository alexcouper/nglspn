import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { CompetitionReveal } from "./CompetitionReveal";
import { fetchCompetition, ApiNotFoundError } from "@/lib/api/server";
import { socialCard } from "@/lib/social-card";

interface PageProps {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { id } = await params;
  try {
    const competition = await fetchCompetition(id);
    const start = new Date(competition.start_date).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
    const end = new Date(competition.submission_deadline).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
    const description = `${competition.name} — ${start} to ${end}`;
    return {
      title: competition.name,
      description,
      ...socialCard({
        title: competition.name,
        description,
        imageUrl: competition.image_url,
      }),
    };
  } catch {
    return {};
  }
}

export default async function CompetitionRevealPage({ params }: PageProps) {
  const { id } = await params;

  let competition;
  try {
    competition = await fetchCompetition(id);
  } catch (err) {
    if (err instanceof ApiNotFoundError) notFound();
    throw err;
  }

  return (
    <main className="min-h-screen bg-muted pt-14">
      <section className="py-8 px-4 sm:px-6">
        <div className="max-w-6xl mx-auto">
          <CompetitionReveal initialCompetition={competition} />
        </div>
      </section>
    </main>
  );
}
