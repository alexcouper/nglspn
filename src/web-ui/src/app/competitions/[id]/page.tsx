import { CompetitionReveal } from "./CompetitionReveal";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function CompetitionRevealPage({ params }: PageProps) {
  const { id } = await params;

  return (
    <main className="min-h-screen bg-muted pt-14">
      <section className="py-8 px-4 sm:px-6">
        <div className="max-w-5xl mx-auto">
          <CompetitionReveal competitionId={id} />
        </div>
      </section>
    </main>
  );
}
