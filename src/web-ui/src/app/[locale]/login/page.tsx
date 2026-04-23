"use client";

import { useState, useCallback, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useAuth } from "@/contexts/auth";
import { getPostAuthDestination } from "@/lib/auth-routing";
import { api, VerifyCodeError } from "@/lib/api";
import { PinInput } from "@/components/PinInput";
import { Translatable } from "@/components/Translatable";

type FlowState = "login" | "forgot" | "code" | "reset";

export default function LoginPage() {
  const t = useTranslations();
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next");
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
      setError(err instanceof Error ? err.message : t("error.loginFailed"));
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
      setError(err instanceof Error ? err.message : t("error.somethingWentWrong"));
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
          setError(err instanceof Error ? err.message : t("error.verificationFailed"));
        }
        setPinKey((k) => k + 1);
      } finally {
        setIsLoading(false);
      }
    },
    [email]
  );

  const handleResetSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      await api.auth.resetPassword(resetToken, newPassword);
      setSuccessMessage(t("auth.reset.successMessage"));
      goToLogin();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error.resetPasswordFailed"));
    } finally {
      setIsLoading(false);
    }
  };

  const renderTitle = (): { headingKey: string; heading: string; subKey: string; sub: string } => {
    switch (flowState) {
      case "login":
        return {
          headingKey: "auth.login.heading",
          heading: t("auth.login.heading"),
          subKey: "auth.login.subheading",
          sub: t("auth.login.subheading"),
        };
      case "forgot":
        return {
          headingKey: "auth.forgot.heading",
          heading: t("auth.forgot.heading"),
          subKey: "auth.forgot.subheading",
          sub: t("auth.forgot.subheading"),
        };
      case "code":
        return {
          headingKey: "auth.code.heading",
          heading: t("auth.code.heading"),
          subKey: "auth.code.subheading",
          sub: t("auth.code.subheading", { email }),
        };
      case "reset":
        return {
          headingKey: "auth.reset.heading",
          heading: t("auth.reset.heading"),
          subKey: "auth.reset.subheading",
          sub: t("auth.reset.subheading"),
        };
    }
  };

  const { headingKey, heading, subKey, sub } = renderTitle();

  return (
    <main className="min-h-screen bg-muted flex items-center justify-center px-4 pt-14">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-semibold text-foreground tracking-tight">
            <Translatable tKey={headingKey}>{heading}</Translatable>
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            <Translatable tKey={subKey}>{sub}</Translatable>
          </p>
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
                <label htmlFor="email" className="label">
                  <Translatable tKey="auth.login.emailLabel">{t("auth.login.emailLabel")}</Translatable>
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input"
                  placeholder={t("auth.login.emailPlaceholder")}
                />
              </div>

              <div>
                <label htmlFor="password" className="label">
                  <Translatable tKey="auth.login.passwordLabel">{t("auth.login.passwordLabel")}</Translatable>
                </label>
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
                {isLoading ? (
                  <Translatable tKey="auth.login.submitting">{t("auth.login.submitting")}</Translatable>
                ) : (
                  <Translatable tKey="auth.login.submit">{t("auth.login.submit")}</Translatable>
                )}
              </button>

              <p className="text-center text-sm text-muted-foreground">
                <button
                  type="button"
                  onClick={() => { setFlowState("forgot"); setError(""); setSuccessMessage(""); }}
                  className="text-accent hover:text-accent-hover font-medium transition-colors"
                >
                  <Translatable tKey="auth.login.forgotPasswordLink">{t("auth.login.forgotPasswordLink")}</Translatable>
                </button>
              </p>
            </form>
          )}

          {flowState === "forgot" && (
            <form onSubmit={handleForgotSubmit} className="space-y-4">
              <div>
                <label htmlFor="forgot-email" className="label">
                  <Translatable tKey="auth.login.emailLabel">{t("auth.login.emailLabel")}</Translatable>
                </label>
                <input
                  id="forgot-email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input"
                  placeholder={t("auth.login.emailPlaceholder")}
                />
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full btn-primary py-2.5"
              >
                {isLoading ? (
                  <Translatable tKey="auth.forgot.submitting">{t("auth.forgot.submitting")}</Translatable>
                ) : (
                  <Translatable tKey="auth.forgot.submit">{t("auth.forgot.submit")}</Translatable>
                )}
              </button>

              <p className="text-center text-sm text-muted-foreground">
                <button
                  type="button"
                  onClick={goToLogin}
                  className="text-accent hover:text-accent-hover font-medium transition-colors"
                >
                  <Translatable tKey="common.backToLogin">{t("common.backToLogin")}</Translatable>
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
                <p className="text-center text-muted-foreground text-sm">
                  <Translatable tKey="auth.code.verifying">{t("auth.code.verifying")}</Translatable>
                </p>
              )}

              {attemptsRemaining !== null && attemptsRemaining > 0 && (
                <p className="text-center text-muted-foreground text-sm">
                  <Translatable tKey="auth.code.attemptsRemaining">
                    {t("auth.code.attemptsRemaining", { count: attemptsRemaining })}
                  </Translatable>
                </p>
              )}

              <p className="text-center text-sm text-muted-foreground">
                <button
                  type="button"
                  onClick={goToLogin}
                  className="text-accent hover:text-accent-hover font-medium transition-colors"
                >
                  <Translatable tKey="common.backToLogin">{t("common.backToLogin")}</Translatable>
                </button>
              </p>
            </div>
          )}

          {flowState === "reset" && (
            <form onSubmit={handleResetSubmit} className="space-y-4">
              <div>
                <label htmlFor="new-password" className="label">
                  <Translatable tKey="auth.reset.passwordLabel">{t("auth.reset.passwordLabel")}</Translatable>
                </label>
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
                {isLoading ? (
                  <Translatable tKey="auth.reset.submitting">{t("auth.reset.submitting")}</Translatable>
                ) : (
                  <Translatable tKey="auth.reset.submit">{t("auth.reset.submit")}</Translatable>
                )}
              </button>

              <p className="text-center text-sm text-muted-foreground">
                <button
                  type="button"
                  onClick={goToLogin}
                  className="text-accent hover:text-accent-hover font-medium transition-colors"
                >
                  <Translatable tKey="common.backToLogin">{t("common.backToLogin")}</Translatable>
                </button>
              </p>
            </form>
          )}

          {flowState === "login" && (
            <p className="mt-6 text-center text-sm text-muted-foreground">
              <Translatable tKey="auth.login.noAccount">{t("auth.login.noAccount")}</Translatable>{" "}
              <Link href={next ? `/register?next=${encodeURIComponent(next)}` : "/register"} className="text-accent hover:text-accent-hover font-medium transition-colors">
                <Translatable tKey="auth.login.createLink">{t("auth.login.createLink")}</Translatable>
              </Link>
            </p>
          )}
        </div>
      </div>
    </main>
  );
}
