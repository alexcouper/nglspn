"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/auth";
import { PinInput } from "@/components/PinInput";
import { getPostAuthDestination } from "@/lib/auth-routing";

export default function VerifyEmailPage() {
  const router = useRouter();
  const { user, isLoading, isAuthenticated, verifyEmail, resendVerification, refreshUser } =
    useAuth();
  const [isVerifying, setIsVerifying] = useState(false);
  const [error, setError] = useState("");
  const [resendCooldown, setResendCooldown] = useState(0);
  const [resendSuccess, setResendSuccess] = useState(false);
  const [inputKey, setInputKey] = useState(0);

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        router.push("/login");
      } else if (user?.is_verified) {
        router.push(getPostAuthDestination(user));
      }
    }
  }, [isLoading, isAuthenticated, user, router]);

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
        const updatedUser = await refreshUser();
        if (updatedUser) {
          router.push(getPostAuthDestination(updatedUser));
        } else {
          router.push("/my-projects");
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Verification failed. Please try again.");
        setInputKey((k) => k + 1);
      } finally {
        setIsVerifying(false);
      }
    },
    [verifyEmail, refreshUser, router]
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
      setError(err instanceof Error ? err.message : "Failed to resend code");
    }
  };

  if (isLoading || !isAuthenticated || user?.is_verified) {
    return (
      <main className="min-h-screen bg-muted flex items-center justify-center">
        <div className="text-muted-foreground text-sm">Loading...</div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-muted flex items-center justify-center px-4 pt-14">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-semibold text-foreground tracking-tight">
            Verify your email
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            We sent a 6-digit code to {user?.email}
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
                Code sent!
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
              <p className="text-center text-muted-foreground text-sm">Verifying...</p>
            )}

            <p className="text-center text-muted-foreground text-sm">
              Didn&apos;t receive the code?{" "}
              <button
                onClick={handleResend}
                disabled={resendCooldown > 0}
                className={`font-medium transition-colors ${
                  resendCooldown > 0
                    ? "text-slate-400 cursor-not-allowed"
                    : "text-accent hover:text-accent-hover"
                }`}
              >
                {resendCooldown > 0 ? `Resend in ${resendCooldown}s` : "Resend"}
              </button>
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
