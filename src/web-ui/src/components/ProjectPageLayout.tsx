"use client";

import { useState, type ReactNode } from "react";

export interface TabDef {
  id: string;
  label: string;
  content: ReactNode;
}

interface ProjectPageLayoutProps {
  banner: ReactNode;
  sidebar: ReactNode;
  tabs: TabDef[];
  winnerBanner?: ReactNode;
}

export function ProjectPageLayout({
  banner,
  sidebar,
  tabs,
  winnerBanner,
}: ProjectPageLayoutProps) {
  const [activeTab, setActiveTab] = useState(tabs[0]?.id ?? "");

  return (
    <>
      {banner}
      <section className="py-8 px-4 sm:px-6">
        <div className="max-w-5xl mx-auto">
          <div className="flex flex-col lg:flex-row gap-8">
            {/* Sidebar */}
            <aside className="w-full lg:w-[280px] flex-shrink-0">
              <div className="lg:sticky lg:top-20 space-y-6">
                {sidebar}
              </div>
            </aside>

            {/* Main content */}
            <div className="flex-1 min-w-0">
              {winnerBanner}

              {/* Tabs */}
              <div className="border-b border-border flex gap-0 mb-6">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === tab.id
                        ? "border-accent text-accent"
                        : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Tab content — render all, hide inactive to preserve state */}
              {tabs.map((tab) => (
                <div
                  key={tab.id}
                  className={activeTab === tab.id ? "" : "hidden"}
                >
                  {tab.content}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
