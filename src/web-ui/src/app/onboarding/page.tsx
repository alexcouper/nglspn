"use client";

import { useEffect, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/auth";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { ONBOARDING_STEP_COMPONENTS } from "@/components/onboarding/steps";

const DEFAULT_DESTINATION = "/my-projects";

export default function OnboardingPage() {
  useRequireAuth();

  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next");
  const { user, isLoading, isAuthenticated, refreshUser } = useAuth();

  const pendingSteps = user?.pending_onboarding_steps ?? [];

  useEffect(() => {
    if (!isLoading && isAuthenticated && pendingSteps.length === 0) {
      router.replace(next ?? DEFAULT_DESTINATION);
    }
  }, [isLoading, isAuthenticated, pendingSteps.length, next, router]);

  const handleStepComplete = useCallback(async () => {
    await refreshUser();
  }, [refreshUser]);

  if (isLoading || !isAuthenticated || !user) {
    return (
      <main className="min-h-screen bg-muted flex items-center justify-center">
        <div className="text-muted-foreground text-sm">Loading...</div>
      </main>
    );
  }

  if (pendingSteps.length === 0) {
    return null;
  }

  const currentStepId = pendingSteps[0];
  const StepComponent = ONBOARDING_STEP_COMPONENTS[currentStepId];

  if (!StepComponent) {
    console.warn(`Unknown onboarding step: ${currentStepId}, skipping`);
    handleStepComplete();
    return null;
  }

  return (
    <main className="min-h-screen bg-muted flex items-center justify-center px-4 pt-14">
      <div className="w-full max-w-sm">
        <StepComponent onComplete={handleStepComplete} />
      </div>
    </main>
  );
}
