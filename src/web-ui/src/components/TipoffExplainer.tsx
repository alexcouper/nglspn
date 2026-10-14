import Link from "next/link";
import { useTranslations } from "next-intl";

import { SITE_EMAIL } from "@/lib/constants";

export function TipoffExplainer() {
  const t = useTranslations("projects.tipoffExplainer");
  return (
    <div className="space-y-2">
      <p className="text-sm text-foreground">
        {t("what")}
      </p>
      <p className="text-sm text-muted-foreground">
        {t.rich("knowOne", {
          link: (chunks) => (
            <Link
              href="/create"
              className="text-accent hover:text-accent-hover underline underline-offset-2"
            >
              {chunks}
            </Link>
          ),
        })}
      </p>
      <p className="text-sm text-muted-foreground">
        {t.rich("claim", {
          email: SITE_EMAIL,
          link: (chunks) => (
            <a
              href={`mailto:${SITE_EMAIL}`}
              className="text-accent hover:text-accent-hover underline underline-offset-2"
            >
              {chunks}
            </a>
          ),
        })}
      </p>
    </div>
  );
}
