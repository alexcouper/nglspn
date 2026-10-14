import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { CompetitionHighlight } from "@/app/components/CompetitionHighlight";
import { fetchCompetitionHighlights } from "@/lib/api/server";
import { SITE_DISCORD_URL, SITE_EMAIL } from "@/lib/constants";

// The prose is markdown, one message per paragraph, joined back into a
// document here so the paragraph breaks stay out of the translators' hands.
const paragraphs = (...blocks: string[]) => blocks.join("\n\n");

export default async function PrizesPage() {
  const t = await getTranslations("about.prizes");
  const { competitions } = await fetchCompetitionHighlights().catch(
    () => ({ competitions: [] })
  );

  const eligibility = paragraphs(
    t("eligibility.whoAndStage"),
    t("eligibility.anySoftware"),
    t("eligibility.sideProjects"),
  );

  const selection = paragraphs(
    t("selection.communityVote"),
    t("selection.frequency"),
    t("selection.sizes"),
    t("selection.getInTouch", { discordUrl: SITE_DISCORD_URL, email: SITE_EMAIL }),
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
            {t("eligibilityTitle")}
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
            {t("selectionTitle")}
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
            {t("readyPrompt")}
          </p>
          <Link href="/register" className="btn-primary">
            {t("getStarted")}
          </Link>
        </div>
      </section>
    </>
  );
}
