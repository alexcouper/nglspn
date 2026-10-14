"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";

const tabs = [
  { href: "/about", key: "what" },
  { href: "/about/why", key: "why" },
  { href: "/about/prizes", key: "prizes" },
  { href: "/about/contact", key: "contact" },
] as const;

export default function AboutLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const t = useTranslations("about.layout");

  return (
    <main className="min-h-screen bg-muted pt-14">
      <section className="bg-nav-bg pt-20 pb-20 px-4 sm:px-6">
        <div className="max-w-4xl mx-auto text-center">
          <p className="text-indigo-400 text-sm font-medium tracking-wide uppercase mb-4">
            {t("kicker")}
          </p>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-white mb-5 tracking-tight leading-[1.1]">
            {t.rich("heading", { br: () => <br /> })}
          </h1>
          <p className="text-lg text-slate-400 max-w-xl mx-auto leading-relaxed">
            {t("intro")}
          </p>
        </div>
      </section>

      <div className="sticky top-14 z-10 bg-white border-b border-border">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 flex items-center gap-6">
          <nav className="flex gap-6 overflow-x-auto scrollbar-hide flex-1" aria-label={t("tabsLabel")}>
            {tabs.map((tab) => {
              const isActive = pathname === tab.href;
              return (
                <Link
                  key={tab.href}
                  href={tab.href}
                  className={`whitespace-nowrap py-3 text-sm font-medium border-b-2 transition-colors ${
                    isActive
                      ? "border-accent text-accent"
                      : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
                  }`}
                >
                  {t(`tabs.${tab.key}`)}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>

      {children}
    </main>
  );
}
