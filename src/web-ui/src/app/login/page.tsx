"use client";

import { useState, useCallback, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useAuth } from "@/contexts/auth";
import { getPostAuthDestination } from "@/lib/auth-routing";
import { api, VerifyCodeError } from "@/lib/api";
import { AuthExpiredError } from "@/lib/api/base";
import { describeApiError } from "@/lib/api/errors";
import { PinInput } from "@/components/PinInput";

type FlowState = "login" | "forgot" | "code" | "reset";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next");
  const t = useTranslations("auth.login");
  const tc = useTranslations("common.actions");
  const { login, isAuthenticated, user, isLoading: authLoading } = useAuth();
  const [flowState, setFlowState] = useState<FlowState>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [resetToken, setResetToken] = useState("");
  const [attemptsRemaining, setAttemptsRemaining] = useState<number | null>(null);
  const [pinKey, setPinKey] = useState(0);

  useEffect(() => {
    if (!authLoading && isAuthenticated && user) {
      router.replace(getPostAuthDestination(user, next));
    }
  }, [authLoading, isAuthenticated, user, next, router]);

  const goToLogin = () => {
    setFlowState("login");
    setError("");
    setNewPassword("");
    setResetToken("");
    setAttemptsRemaining(null);
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccessMessage("");
    setIsLoading(true);

    try {
      const userData = await login(email, password);
      router.push(getPostAuthDestination(userData, next));
    } catch (err) {
      // Nobody on this screen has a session yet, so the 401 the API layer turns
      // into AuthExpiredError means the credentials just typed were rejected —
      // not that a session ran out. "Sign in again" would be nonsense here.
      setError(
        err instanceof AuthExpiredError
          ? t("errors.invalidCredentials")
          : describeApiError(err, t("errors.loginFailed")),
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleForgotSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      await api.auth.forgotPassword(email);
      setFlowState("code");
    } catch (err) {
      setError(describeApiError(err, t("errors.sendCodeFailed")));
    } finally {
      setIsLoading(false);
    }
  };

  const handleCodeComplete = useCallback(
    async (code: string) => {
      setError("");
      setIsLoading(true);

      try {
        const result = await api.auth.forgotPasswordVerify(email, code);
        setResetToken(result.reset_token);
        setFlowState("reset");
      } catch (err) {
        if (err instanceof VerifyCodeError) {
          setAttemptsRemaining(err.attemptsRemaining);
          setError(err.message);
        } else {
          setError(describeApiError(err, t("errors.checkCodeFailed")));
        }
        setPinKey((k) => k + 1);
      } finally {
        setIsLoading(false);
      }
    },
    [email, t]
  );

  const handleResetSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      await api.auth.resetPassword(resetToken, newPassword);
      setSuccessMessage(t("passwordUpdated"));
      goToLogin();
    } catch (err) {
      setError(describeApiError(err, t("errors.resetFailed")));
    } finally {
      setIsLoading(false);
    }
  };

  const renderTitle = () => {
    switch (flowState) {
      case "login":
        return { heading: t("title"), sub: t("subtitle") };
      case "forgot":
        return { heading: t("forgotTitle"), sub: t("forgotSubtitle") };
      case "code":
        return { heading: t("codeTitle"), sub: t("codeSubtitle", { email }) };
      case "reset":
        return { heading: t("resetTitle"), sub: t("resetSubtitle") };
    }
  };

  const { heading, sub } = renderTitle();

  return (
    <main className="min-h-screen bg-muted flex items-center justify-center px-4 pt-14">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-semibold text-foreground tracking-tight">
            {heading}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">{sub}</p>
        </div>

        <div className="bg-white border border-border rounded-xl p-6 shadow-sm">
          {successMessage && (
            <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 px-3 py-2.5 rounded-lg text-sm mb-4">
              {successMessage}
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2.5 rounded-lg text-sm mb-4">
              {error}
            </div>
          )}

          {flowState === "login" && (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label htmlFor="email" className="label">{t("email")}</label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input"
                  placeholder={t("emailPlaceholder")}
                />
              </div>

              <div>
                <label htmlFor="password" className="label">{t("password")}</label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input"
                />
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full btn-primary py-2.5"
              >
                {isLoading ? t("submitting") : t("submit")}
              </button>

              <p className="text-center text-sm text-muted-foreground">
                <button
                  type="button"
                  onClick={() => { setFlowState("forgot"); setError(""); setSuccessMessage(""); }}
                  className="text-accent hover:text-accent-hover font-medium transition-colors"
                >
                  {t("forgotLink")}
                </button>
              </p>
            </form>
          )}

          {flowState === "forgot" && (
            <form onSubmit={handleForgotSubmit} className="space-y-4">
              <div>
                <label htmlFor="forgot-email" className="label">{t("email")}</label>
                <input
                  id="forgot-email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input"
                  placeholder={t("emailPlaceholder")}
                />
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full btn-primary py-2.5"
              >
                {isLoading ? tc("sending") : tc("continue")}
              </button>

              <p className="text-center text-sm text-muted-foreground">
                <button
                  type="button"
                  onClick={goToLogin}
                  className="text-accent hover:text-accent-hover font-medium transition-colors"
                >
                  {t("backToLogin")}
                </button>
              </p>
            </form>
          )}

          {flowState === "code" && (
            <div className="space-y-5">
              <div className="py-2">
                <PinInput
                  key={pinKey}
                  onComplete={handleCodeComplete}
                  disabled={isLoading}
                  hasError={!!error}
                />
              </div>

              {isLoading && (
                <p className="text-center text-muted-foreground text-sm">{t("verifying")}</p>
              )}

              {attemptsRemaining !== null && attemptsRemaining > 0 && (
                <p className="text-center text-muted-foreground text-sm">
                  {t("attemptsRemaining", { count: attemptsRemaining })}
                </p>
              )}

              <p className="text-center text-sm text-muted-foreground">
                <button
                  type="button"
                  onClick={goToLogin}
                  className="text-accent hover:text-accent-hover font-medium transition-colors"
                >
                  {t("backToLogin")}
                </button>
              </p>
            </div>
          )}

          {flowState === "reset" && (
            <form onSubmit={handleResetSubmit} className="space-y-4">
              <div>
                <label htmlFor="new-password" className="label">{t("newPassword")}</label>
                <input
                  id="new-password"
                  name="new-password"
                  type="password"
                  autoComplete="new-password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="input"
                />
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full btn-primary py-2.5"
              >
                {isLoading ? tc("saving") : t("setPassword")}
              </button>

              <p className="text-center text-sm text-muted-foreground">
                <button
                  type="button"
                  onClick={goToLogin}
                  className="text-accent hover:text-accent-hover font-medium transition-colors"
                >
                  {t("backToLogin")}
                </button>
              </p>
            </form>
          )}

          {flowState === "login" && (
            <p className="mt-6 text-center text-sm text-muted-foreground">
              {t("noAccount")}{" "}
              <Link href={next ? `/register?next=${encodeURIComponent(next)}` : "/register"} className="text-accent hover:text-accent-hover font-medium transition-colors">
                {t("createOne")}
              </Link>
            </p>
          )}
        </div>
      </div>
    </main>
  );
}
