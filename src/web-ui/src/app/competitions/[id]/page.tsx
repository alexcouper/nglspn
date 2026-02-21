import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { CompetitionReveal } from "./CompetitionReveal";
import { fetchCompetition, getAllCompetitionSlugs } from "@/lib/api/server";
export const revalidate = 3600;

interface PageProps {
  params: Promise<{ id: string }>;
}

export async function generateStaticParams() {
  const slugs = await getAllCompetitionSlugs();
  return slugs.map((id) => ({ id }));
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
    const end = new Date(competition.end_date).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
    return {
      title: competition.name,
      description: `${competition.name} — ${start} to ${end}`,
      openGraph: {
        title: competition.name,
        description: `${competition.name} — ${start} to ${end}`,
        ...(competition.image_url && {
          images: [{ url: competition.image_url }],
        }),
      },
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
  } catch {
    notFound();
  }

  return (
    <main className="min-h-screen bg-muted pt-14">
      <section className="py-8 px-4 sm:px-6">
        <div className="max-w-5xl mx-auto">
          <CompetitionReveal initialCompetition={competition} />
        </div>
      </section>
    </main>
  );
}
