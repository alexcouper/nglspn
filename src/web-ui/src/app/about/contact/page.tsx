import { getTranslations } from "next-intl/server";
import { SITE_DISCORD_URL, SITE_EMAIL } from "@/lib/constants";

export default async function ContactPage() {
  const t = await getTranslations("about.contact");
  return (
    <section className="py-12 px-4 sm:px-6 bg-white">
      <div className="max-w-3xl mx-auto">
        <h2 className="text-lg font-semibold text-foreground tracking-tight mb-4">
          {t("title")}
        </h2>
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground w-16">{t("discord")}</span>
            <a
              href={SITE_DISCORD_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-accent hover:text-accent-hover transition-colors"
            >
              {SITE_DISCORD_URL.replace(/^https:\/\//, "")}
            </a>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground w-16">{t("email")}</span>
            <a
              href={`mailto:${SITE_EMAIL}`}
              className="text-sm text-accent hover:text-accent-hover transition-colors"
            >
              {SITE_EMAIL}
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
