import type { Metadata } from "next";
import ReactMarkdown from "react-markdown";
import { getTranslations } from "next-intl/server";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("about.privacy");
  return { title: t("metaTitle") };
}

// The policy is markdown, one message per heading, paragraph or list item.
// The document structure (heading levels, which items form a list) is
// assembled here so translators only ever see prose.
const blocks = (...parts: string[]) => parts.join("\n\n");
const section = (heading: string, ...body: string[]) => blocks(`## ${heading}`, ...body);
const bullets = (...items: string[]) => items.map((item) => `- ${item}`).join("\n");

export default async function PrivacyPolicyPage() {
  const t = await getTranslations("about.privacy");

  const content = blocks(
    `# ${t("title")}`,
    t("lastUpdated"),
    section(t("whoWeAre.heading"), t("whoWeAre.operator"), t("whoWeAre.controller")),
    section(
      t("whatWeCollect.heading"),
      t("whatWeCollect.intro"),
      bullets(t("whatWeCollect.account"), t("whatWeCollect.identity"), t("whatWeCollect.content")),
      t("whatWeCollect.technical"),
    ),
    section(
      t("legalBasis.heading"),
      t("legalBasis.intro"),
      bullets(t("legalBasis.contract"), t("legalBasis.legitimateInterest"), t("legalBasis.consent")),
    ),
    section(t("howWeUse.heading"), t("howWeUse.purposes"), t("howWeUse.noThirdParty")),
    section(t("sharing.heading"), t("sharing.noSale"), t("sharing.processors"), t("sharing.publicContent")),
    section(t("storage.heading"), t("storage.text")),
    section(t("retention.heading"), t("retention.account"), t("retention.logs")),
    section(t("cookies.heading"), t("cookies.text")),
    section(
      t("rights.heading"),
      t("rights.intro"),
      bullets(
        t("rights.access"),
        t("rights.correct"),
        t("rights.delete"),
        t("rights.portability"),
        t("rights.restrict"),
        t("rights.object"),
        t("rights.withdraw"),
      ),
      t("rights.manage"),
      t("rights.complaint"),
    ),
    section(t("changes.heading"), t("changes.text")),
    section(t("contact.heading"), t("contact.text")),
  );

  return (
    <section className="py-12 px-4 sm:px-6 bg-white">
      <div className="max-w-3xl mx-auto">
        <article className="article markdown">
          <ReactMarkdown>{content}</ReactMarkdown>
        </article>
      </div>
    </section>
  );
}
