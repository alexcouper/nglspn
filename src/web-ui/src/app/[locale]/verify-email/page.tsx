"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Translatable } from "@/components/Translatable";

export default function VerifyEmailPage() {
  const t = useTranslations();
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next");

  useEffect(() => {
    const params = next ? `?next=${encodeURIComponent(next)}` : "";
    router.replace(`/onboarding${params}`);
  }, [next, router]);

  return (
    <main className="min-h-screen bg-muted flex items-center justify-center">
      <div className="text-muted-foreground text-sm">
        <Translatable tKey="common.loading">{t("common.loading")}</Translatable>
      </div>
    </main>
  );
}
