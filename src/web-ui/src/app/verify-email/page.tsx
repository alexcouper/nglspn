"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";

export default function VerifyEmailPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next");
  const t = useTranslations("common");

  useEffect(() => {
    const params = next ? `?next=${encodeURIComponent(next)}` : "";
    router.replace(`/onboarding${params}`);
  }, [next, router]);

  return (
    <main className="min-h-screen bg-muted flex items-center justify-center">
      <div className="text-muted-foreground text-sm">{t("loading")}</div>
    </main>
  );
}
