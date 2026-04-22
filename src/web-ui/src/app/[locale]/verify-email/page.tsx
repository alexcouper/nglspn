"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function VerifyEmailPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next");

  useEffect(() => {
    const params = next ? `?next=${encodeURIComponent(next)}` : "";
    router.replace(`/onboarding${params}`);
  }, [next, router]);

  return (
    <main className="min-h-screen bg-muted flex items-center justify-center">
      <div className="text-muted-foreground text-sm">Loading...</div>
    </main>
  );
}
