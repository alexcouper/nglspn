import { Suspense, type ReactNode } from "react";

export default function LegacyProjectsLayout({ children }: { children: ReactNode }) {
  return <Suspense>{children}</Suspense>;
}
