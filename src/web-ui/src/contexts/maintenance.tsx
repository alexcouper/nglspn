"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import Image from "next/image";

interface MaintenanceConfig {
  enabled: boolean;
  message?: string;
  estimatedEnd?: string;
}

interface MaintenanceContextType {
  isMaintenanceMode: boolean;
  config: MaintenanceConfig | null;
  isLoading: boolean;
}

const MaintenanceContext = createContext<MaintenanceContextType | undefined>(undefined);

const CDN_CONFIG_URL = "https://cdn.naglasupan.is/maintenance/config.json";
const LOCAL_CONFIG_URL = "/maintenance.json";

function getConfigUrl(): string {
  if (process.env.NEXT_PUBLIC_USE_LOCAL_MAINTENANCE === "true") {
    return LOCAL_CONFIG_URL;
  }
  return CDN_CONFIG_URL;
}

function hasBypassCookie(): boolean {
  if (typeof document === "undefined") return false;
  return document.cookie.split(";").some((c) => c.trim().startsWith("maintenance_bypass="));
}

export function MaintenanceProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<MaintenanceConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchMaintenanceConfig = async () => {
      const configUrl = getConfigUrl();

      try {
        // Add cache-buster to bypass CDN caching
        const url = `${configUrl}?_=${Date.now()}`;
        const response = await fetch(url, {
          cache: "no-store",
        });

        if (response.ok) {
          const data = await response.json();
          setConfig(data);
        } else {
          // If config not found, assume no maintenance
          setConfig({ enabled: false });
        }
      } catch {
        // On error, assume no maintenance (don't block the app)
        setConfig({ enabled: false });
      } finally {
        setIsLoading(false);
      }
    };

    fetchMaintenanceConfig();
  }, []);

  const hasBypass = hasBypassCookie();
  const isMaintenanceMode = (config?.enabled ?? false) && !hasBypass;

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-pulse text-muted-foreground">Loading...</div>
      </div>
    );
  }

  if (isMaintenanceMode) {
    return <MaintenancePage config={config!} />;
  }

  return (
    <MaintenanceContext.Provider value={{ isMaintenanceMode, config, isLoading }}>
      {children}
    </MaintenanceContext.Provider>
  );
}

export function useMaintenance() {
  const context = useContext(MaintenanceContext);
  if (context === undefined) {
    throw new Error("useMaintenance must be used within a MaintenanceProvider");
  }
  return context;
}

function MaintenancePage({ config }: { config: MaintenanceConfig }) {
  return (
    <main className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="max-w-lg w-full text-center">
        <div className="mb-8">
          <Image
            src="/icons/app/logo-1.svg"
            alt="naglasúpan"
            width={120}
            height={120}
            className="mx-auto opacity-80"
          />
        </div>

        <h1 className="text-3xl md:text-4xl font-semibold text-foreground mb-4">
          We&apos;ll be back soon
        </h1>

        <p className="text-lg md:text-xl text-muted-foreground mb-6 leading-relaxed">
          {config.message || "We're making some improvements. Please check back shortly."}
        </p>

        {config.estimatedEnd && (
          <p className="text-sm text-muted-foreground mb-8">
            Expected to be back: {config.estimatedEnd}
          </p>
        )}

        <div className="inline-flex items-center gap-2 px-4 py-2 bg-muted rounded-lg text-sm font-medium text-muted-foreground">
          <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
          Under Maintenance
        </div>

        <p className="mt-10 text-sm text-muted-foreground">
          Questions? Join us on{" "}
          <a
            href="https://discord.gg/DqUV64g7JE"
            target="_blank"
            rel="noopener noreferrer"
            className="text-accent hover:text-accent-hover underline underline-offset-2"
          >
            Discord
          </a>
        </p>

        <p className="mt-6 text-sm text-muted-foreground/50">
          naglasúpan
        </p>
      </div>
    </main>
  );
}
