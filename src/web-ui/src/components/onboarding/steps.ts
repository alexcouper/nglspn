import type { ComponentType } from "react";
import { VerifyEmailStep } from "./VerifyEmailStep";

export interface OnboardingStepProps {
  onComplete: () => void;
}

export const ONBOARDING_STEP_COMPONENTS: Record<string, ComponentType<OnboardingStepProps>> = {
  "verify-email": VerifyEmailStep,
};
