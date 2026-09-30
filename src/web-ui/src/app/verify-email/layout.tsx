import { Suspense, type ReactNode } from "react";

export default function VerifyEmailLayout({ children }: { children: ReactNode }) {
  return <Suspense>{children}</Suspense>;
}
