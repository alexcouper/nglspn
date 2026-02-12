"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const tabs = [
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
      <section className="bg-white border-b border-border py-10 px-4 sm:px-6">
        <div className="max-w-3xl mx-auto">
          <h1 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight mb-5">
            About
          </h1>

          <div className="flex gap-1">
            {tabs.map((tab) => {
              const isActive = pathname === tab.href;
              return (
                <Link
                  key={tab.href}
                  href={tab.href}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-accent text-white"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  }`}
                >
                  {tab.label}
                </Link>
              );
            })}
          </div>
        </div>
      </section>

      {children}
    </main>
  );
}
