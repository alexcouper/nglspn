import { Suspense, type ReactNode } from "react";

export default function ProjectsLayout({ children }: { children: ReactNode }) {
  return <Suspense>{children}</Suspense>;
}
