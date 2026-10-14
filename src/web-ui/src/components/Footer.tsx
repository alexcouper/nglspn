import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { SITE_DISCORD_URL } from "@/lib/constants";

export async function Footer() {
  const t = await getTranslations("common.footer");
  return (
    <footer className="border-t border-border bg-white mt-auto">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
        <div className="flex justify-center">
          <nav className="flex flex-wrap justify-center gap-x-6 gap-y-2 text-sm" aria-label={t("label")}>
            <Link href="/guides" className="text-muted-foreground hover:text-foreground transition-colors">
              {t("guides")}
            </Link>
            <Link href="/is/guides" lang="is" hrefLang="is" className="text-muted-foreground hover:text-foreground transition-colors">
              {t("guidesIcelandic")}
            </Link>
            <Link
              href="/about"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              {t("about")}
            </Link>
            <Link
              href="/privacy"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              {t("privacy")}
            </Link>
            <a
              href={SITE_DISCORD_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              {t("discord")}
            </a>
          </nav>
        </div>
      </div>
    </footer>
  );
}
