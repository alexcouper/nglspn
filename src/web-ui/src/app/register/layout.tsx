import { Suspense, type ReactNode } from "react";

export default function RegisterLayout({ children }: { children: ReactNode }) {
  return <Suspense>{children}</Suspense>;
}
