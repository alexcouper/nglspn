"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const tabs = [
  { href: "/about", label: "What" },
  { href: "/about/why", label: "Why" },
  { href: "/about/prizes", label: "Prizes" },
  { href: "/about/contact", label: "Contact" },
];

export default function AboutLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <main className="min-h-screen bg-muted pt-14">
      <section className="bg-nav-bg pt-20 pb-20 px-4 sm:px-6">
        <div className="max-w-4xl mx-auto text-center">
          <p className="text-indigo-400 text-sm font-medium tracking-wide uppercase mb-4">
            Iceland&apos;s builder community
          </p>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-white mb-5 tracking-tight leading-[1.1]">
            Shine a light on
            <br />
            your work
          </h1>
          <p className="text-lg text-slate-400 max-w-xl mx-auto leading-relaxed">
            A platform for Icelandic developers to showcase side projects,
            get feedback from the community, and compete for recognition.
          </p>
        </div>
      </section>

      <div className="sticky top-14 z-10 bg-white border-b border-border">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 flex items-center gap-6">
          <nav className="flex gap-6 overflow-x-auto scrollbar-hide flex-1" aria-label="About tabs">
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
                  {tab.label}
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
