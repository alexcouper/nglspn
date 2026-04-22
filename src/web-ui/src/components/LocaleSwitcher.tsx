"use client";

import { useLocale } from "next-intl";
import { usePathname, useRouter } from "@/i18n/navigation";
import { locales, localeLabels, type Locale } from "@/i18n/config";

export function LocaleSwitcher({ className }: { className?: string }) {
  const locale = useLocale() as Locale;
  const pathname = usePathname();
  const router = useRouter();

  const other = locales.find((l) => l !== locale) ?? locale;

  return (
    <button
      type="button"
      onClick={() => router.replace(pathname, { locale: other })}
      className={className ?? "text-sm text-slate-400 hover:text-white transition-colors"}
      aria-label={`Switch to ${localeLabels[other]}`}
    >
      {localeLabels[other]}
    </button>
  );
}
