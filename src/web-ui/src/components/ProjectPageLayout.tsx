"use client";

import { useState, useEffect, useCallback, type ReactNode } from "react";

export interface TabDef {
  id: string;
  label: ReactNode;
  content: ReactNode;
}

interface ProjectPageLayoutProps {
  banner: ReactNode;
  sidebar: ReactNode;
  tabs: TabDef[];
  winnerBanner?: ReactNode;
}

function getTabFromHash(tabs: TabDef[]): string | null {
  if (typeof window === "undefined") return null;
  const hash = window.location.hash.slice(1);
  return tabs.some((t) => t.id === hash) ? hash : null;
}

export function ProjectPageLayout({
  banner,
  sidebar,
  tabs,
  winnerBanner,
}: ProjectPageLayoutProps) {
  const [activeTab, setActiveTab] = useState(
    () => getTabFromHash(tabs) ?? tabs[0]?.id ?? ""
  );

  useEffect(() => {
    const onHashChange = () => {
      const tab = getTabFromHash(tabs);
      if (tab) setActiveTab(tab);
    };
    window.addEventListener("hashchange", onHashChange);
    // Sync on mount — router.push doesn't fire hashchange
    window.dispatchEvent(new HashChangeEvent("hashchange"));
    return () => window.removeEventListener("hashchange", onHashChange);
  }, [tabs]);

  const selectTab = useCallback(
    (id: string) => {
      setActiveTab(id);
      const defaultTab = tabs[0]?.id;
      if (id === defaultTab) {
        history.replaceState(null, "", window.location.pathname + window.location.search);
      } else {
        history.replaceState(null, "", `#${id}`);
      }
    },
    [tabs]
  );

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
                    onClick={() => selectTab(tab.id)}
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
