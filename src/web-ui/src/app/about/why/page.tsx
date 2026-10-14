import ReactMarkdown from "react-markdown";
import { getTranslations } from "next-intl/server";

// The prose is markdown, one message per paragraph or list item, joined back
// into a document here so the structure stays out of the translators' hands.
const paragraphs = (...blocks: string[]) => blocks.join("\n\n");
const bullets = (...items: string[]) => items.map((item) => ` - ${item}`).join("\n");

export default async function WhyPage() {
  const t = await getTranslations("about.why");

  const why = paragraphs(
    t("ambition.beMoreAmbitious"),
    t("ambition.fragileIdeas"),
    t("ambition.whyWeNeedThem"),
    t("ambition.whatNaglasupanDoes"),
  );

  const pocSection = paragraphs(
    t("poc.cheaperThanEver"),
    `${t("poc.needsIntro")}\n${bullets(
      t("poc.needs.building"),
      t("poc.needs.feedback"),
      t("poc.needs.adoption"),
    )}`,
  );

  const seniorSection = paragraphs(
    t("senior.aiCloning"),
    t("senior.extinctionEvent"),
    t("senior.encourageNewer"),
    t("senior.communityInvests"),
  );

  const geopoliticsSection = paragraphs(
    t("geopolitics.builtAndHostedHere"),
    t("geopolitics.risk"),
    t("geopolitics.sharedInfrastructure"),
  );

  return (
    <>
      <section className="py-12 px-4 sm:px-6 bg-white">
        <div className="max-w-3xl mx-auto">
          <article className="article markdown">
            <ReactMarkdown>{why}</ReactMarkdown>
          </article>
        </div>
      </section>

      <section className="py-12 px-4 sm:px-6 bg-muted">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-lg font-semibold text-foreground tracking-tight mb-4">
            {t("pocTitle")}
          </h2>
          <article className="article markdown">
            <ReactMarkdown>{pocSection}</ReactMarkdown>
          </article>
        </div>
      </section>

      <section className="py-12 px-4 sm:px-6 bg-white">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-lg font-semibold text-foreground tracking-tight mb-4">
            {t("seniorTitle")}
          </h2>
          <article className="article markdown">
            <ReactMarkdown>{seniorSection}</ReactMarkdown>
          </article>
        </div>
      </section>

      <section className="py-12 px-4 sm:px-6 bg-muted">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-lg font-semibold text-foreground tracking-tight mb-4">
            {t("geopoliticsTitle")}
          </h2>
          <article className="article markdown">
            <ReactMarkdown>{geopoliticsSection}</ReactMarkdown>
          </article>
        </div>
      </section>
    </>
  );
}
