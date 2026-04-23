import { getTranslations } from "next-intl/server";
import { Translatable } from "@/components/Translatable";

export default async function ContactPage() {
  const t = await getTranslations();
  return (
    <section className="py-12 px-4 sm:px-6 bg-white">
      <div className="max-w-3xl mx-auto">
        <h2 className="text-lg font-semibold text-foreground tracking-tight mb-4">
          <Translatable tKey="about.contact.heading">{t("about.contact.heading")}</Translatable>
        </h2>
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground w-16">
              <Translatable tKey="about.contact.discordLabel">{t("about.contact.discordLabel")}</Translatable>
            </span>
            <a
              href="https://discord.gg/D47bQjaQ"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-accent hover:text-accent-hover transition-colors"
            >
              discord.gg/D47bQjaQ
            </a>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground w-16">
              <Translatable tKey="about.contact.emailLabel">{t("about.contact.emailLabel")}</Translatable>
            </span>
            <a
              href="mailto:alex@naglasupan.is"
              className="text-sm text-accent hover:text-accent-hover transition-colors"
            >
              alex@naglasupan.is
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
