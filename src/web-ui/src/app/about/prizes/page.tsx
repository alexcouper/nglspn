import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Link from "next/link";
import { CompetitionHighlight } from "@/app/components/CompetitionHighlight";
import { fetchCompetitionHighlights } from "@/lib/api/server";

const eligibility = `
Projects must be built by Iceland-based developers. Projects can be at any stage of development, from idea to launched product.

The aim is to encourage general software development too, so web apps, mobile apps, desktop apps, libraries, CLIs, etc are all fair game.

Initially the focus is on side projects, but if you have a full time project that you're working on that you're willing to share and get feedback on, that's fine too.
`;

const selection = `
Winners are selected by the community. During each competition's voting phase, registered members rank the entered projects, and the rankings are aggregated to decide the winner.

Prize frequency will be variable dependent on uptake, but somewhere in the weekly-monthly range.

Prize sizes and quantity will depend on sponsorships, but we're good for a few months at least.

If you'd like to help shape how competitions are run, get in touch via [discord](https://discord.gg/D47bQjaQ) or [email](mailto:alex@naglasupan.is).
`;

export default async function PrizesPage() {
  const { competitions } = await fetchCompetitionHighlights().catch(
    () => ({ competitions: [] })
  );
  return (
    <>
      <section className="py-12 px-4 sm:px-6 bg-white border-b border-border">
        <div className="max-w-5xl mx-auto">
          <CompetitionHighlight competitions={competitions ?? []} />
        </div>
      </section>

      <section className="py-12 px-4 sm:px-6 bg-white">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-lg font-semibold text-foreground tracking-tight mb-4">
            Eligibility
          </h2>
          <article className="article markdown">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {eligibility}
            </ReactMarkdown>
          </article>
        </div>
      </section>

      <section className="py-12 px-4 sm:px-6 bg-muted">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-lg font-semibold text-foreground tracking-tight mb-4">
            Prize giving and selection
          </h2>
          <article className="article markdown">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {selection}
            </ReactMarkdown>
          </article>
        </div>
      </section>

      <section className="py-12 px-4 sm:px-6 bg-white">
        <div className="max-w-2xl mx-auto text-center">
          <p className="text-foreground font-medium mb-5">
            Ready to submit your project?
          </p>
          <Link href="/register" className="btn-primary">
            Get started
          </Link>
        </div>
      </section>
    </>
  );
}
