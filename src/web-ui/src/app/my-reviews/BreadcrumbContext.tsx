"use client";

import { createContext, useContext, useState, useCallback } from "react";

interface BreadcrumbData {
  competitionName?: string;
  projectTitle?: string;
}

interface BreadcrumbContextType {
  data: BreadcrumbData;
  setCompetitionName: (name: string) => void;
  setProjectTitle: (title: string) => void;
  clear: () => void;
}

const BreadcrumbContext = createContext<BreadcrumbContextType | null>(null);

export function BreadcrumbProvider({ children }: { children: React.ReactNode }) {
  const [data, setData] = useState<BreadcrumbData>({});

  const setCompetitionName = useCallback((name: string) => {
    setData((prev) => ({ ...prev, competitionName: name }));
  }, []);

  const setProjectTitle = useCallback((title: string) => {
    setData((prev) => ({ ...prev, projectTitle: title }));
  }, []);

  const clear = useCallback(() => {
    setData({});
  }, []);

  return (
    <BreadcrumbContext.Provider
      value={{ data, setCompetitionName, setProjectTitle, clear }}
    >
      {children}
    </BreadcrumbContext.Provider>
  );
}

export function useBreadcrumbs() {
  const context = useContext(BreadcrumbContext);
  if (!context) {
    throw new Error("useBreadcrumbs must be used within BreadcrumbProvider");
  }
  return context;
}
