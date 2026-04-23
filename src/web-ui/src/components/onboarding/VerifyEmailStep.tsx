"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { useAuth } from "@/contexts/auth";
import { PinInput } from "@/components/PinInput";
import { Translatable } from "@/components/Translatable";

interface VerifyEmailStepProps {
  onComplete: () => void;
}

export function VerifyEmailStep({ onComplete }: VerifyEmailStepProps) {
  const t = useTranslations();
  const { user, verifyEmail, resendVerification } = useAuth();
  const [isVerifying, setIsVerifying] = useState(false);
  const [error, setError] = useState("");
  const [resendCooldown, setResendCooldown] = useState(0);
  const [resendSuccess, setResendSuccess] = useState(false);
  const [inputKey, setInputKey] = useState(0);

  useEffect(() => {
    if (resendCooldown > 0) {
      const timer = setTimeout(() => setResendCooldown(resendCooldown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [resendCooldown]);

  const handleComplete = useCallback(
    async (code: string) => {
      setError("");
      setIsVerifying(true);

      try {
        await verifyEmail(code);
        onComplete();
      } catch (err) {
        setError(err instanceof Error ? err.message : t("error.verificationFailedRetry"));
        setInputKey((k) => k + 1);
      } finally {
        setIsVerifying(false);
      }
    },
    [verifyEmail, onComplete, t]
  );

  const handleResend = async () => {
    if (resendCooldown > 0) return;

    try {
      await resendVerification();
      setResendSuccess(true);
      setResendCooldown(60);
      setError("");
      setTimeout(() => setResendSuccess(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error.resendCodeFailed"));
    }
  };

  return (
    <>
      <div className="text-center mb-8">
        <h1 className="text-2xl font-semibold text-foreground tracking-tight">
          <Translatable tKey="onboarding.verifyEmail.heading">{t("onboarding.verifyEmail.heading")}</Translatable>
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          <Translatable tKey="onboarding.verifyEmail.subheading">
            {t("onboarding.verifyEmail.subheading", { email: user?.email ?? "" })}
          </Translatable>
        </p>
      </div>

      <div className="bg-white border border-border rounded-xl p-6 shadow-sm">
        <div className="space-y-5">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2.5 rounded-lg text-sm text-center">
              {error}
            </div>
          )}

          {resendSuccess && (
            <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 px-3 py-2.5 rounded-lg text-sm text-center">
              <Translatable tKey="onboarding.verifyEmail.codeSentMessage">{t("onboarding.verifyEmail.codeSentMessage")}</Translatable>
            </div>
          )}

          <div className="py-2">
            <PinInput
              key={inputKey}
              onComplete={handleComplete}
              disabled={isVerifying}
              hasError={!!error}
            />
          </div>

          {isVerifying && (
            <p className="text-center text-muted-foreground text-sm">
              <Translatable tKey="onboarding.verifyEmail.verifying">{t("onboarding.verifyEmail.verifying")}</Translatable>
            </p>
          )}

          <p className="text-center text-muted-foreground text-sm">
            <Translatable tKey="onboarding.verifyEmail.noCode">{t("onboarding.verifyEmail.noCode")}</Translatable>{" "}
            <button
              onClick={handleResend}
              disabled={resendCooldown > 0}
              className={`font-medium transition-colors ${
                resendCooldown > 0
                  ? "text-slate-400 cursor-not-allowed"
                  : "text-accent hover:text-accent-hover"
              }`}
            >
              {resendCooldown > 0 ? (
                <Translatable tKey="onboarding.verifyEmail.resendCooldown">
                  {t("onboarding.verifyEmail.resendCooldown", { count: resendCooldown })}
                </Translatable>
              ) : (
                <Translatable tKey="onboarding.verifyEmail.resend">{t("onboarding.verifyEmail.resend")}</Translatable>
              )}
            </button>
          </p>
        </div>
      </div>
    </>
  );
}
