import { Link } from "@/i18n/navigation";
import { useTranslations } from "next-intl";
import { Translatable } from "./Translatable";

export function Footer() {
  const t = useTranslations("footer");
  return (
    <footer className="border-t border-border bg-white mt-auto">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
        <div className="flex justify-center">
          <nav className="flex flex-wrap justify-center gap-x-6 gap-y-2 text-sm" aria-label="Footer">
            <Link
              href="/about"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              <Translatable tKey="footer.about">{t("about")}</Translatable>
            </Link>
            <Link
              href="/privacy"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              <Translatable tKey="footer.privacy">{t("privacy")}</Translatable>
            </Link>
            <a
              href="https://discord.gg/D47bQjaQ"
              target="_blank"
              rel="noopener noreferrer"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              <Translatable tKey="footer.discord">{t("discord")}</Translatable>
            </a>
          </nav>
        </div>
      </div>
    </footer>
  );
}
