"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/auth";
import { getPostAuthDestination } from "@/lib/auth-routing";
import { api, VerifyCodeError } from "@/lib/api";
import { PinInput } from "@/components/PinInput";

type FlowState = "login" | "forgot" | "code" | "reset";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
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
      router.push(getPostAuthDestination(userData));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
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
      setError(err instanceof Error ? err.message : "Something went wrong");
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
          setError(err instanceof Error ? err.message : "Verification failed");
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
      setSuccessMessage("Password updated. Please log in.");
      goToLogin();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reset password");
    } finally {
      setIsLoading(false);
    }
  };

  const renderTitle = () => {
    switch (flowState) {
      case "login":
        return { heading: "Welcome back", sub: "Log in to manage your projects" };
      case "forgot":
        return { heading: "Forgotten password?", sub: "Enter your email to receive a reset code" };
      case "code":
        return { heading: "Enter your code", sub: `We sent a 6-digit code to ${email}` };
      case "reset":
        return { heading: "Set new password", sub: "Choose a new password for your account" };
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
                <label htmlFor="email" className="label">Email</label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input"
                  placeholder="you@example.com"
                />
              </div>

              <div>
                <label htmlFor="password" className="label">Password</label>
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
                {isLoading ? "Logging in..." : "Log In"}
              </button>

              <p className="text-center text-sm text-muted-foreground">
                <button
                  type="button"
                  onClick={() => { setFlowState("forgot"); setError(""); setSuccessMessage(""); }}
                  className="text-accent hover:text-accent-hover font-medium transition-colors"
                >
                  Forgotten password?
                </button>
              </p>
            </form>
          )}

          {flowState === "forgot" && (
            <form onSubmit={handleForgotSubmit} className="space-y-4">
              <div>
                <label htmlFor="forgot-email" className="label">Email</label>
                <input
                  id="forgot-email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input"
                  placeholder="you@example.com"
                />
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full btn-primary py-2.5"
              >
                {isLoading ? "Sending..." : "Continue"}
              </button>

              <p className="text-center text-sm text-muted-foreground">
                <button
                  type="button"
                  onClick={goToLogin}
                  className="text-accent hover:text-accent-hover font-medium transition-colors"
                >
                  Back to login
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
                <p className="text-center text-muted-foreground text-sm">Verifying...</p>
              )}

              {attemptsRemaining !== null && attemptsRemaining > 0 && (
                <p className="text-center text-muted-foreground text-sm">
                  {attemptsRemaining} {attemptsRemaining === 1 ? "attempt" : "attempts"} remaining
                </p>
              )}

              <p className="text-center text-sm text-muted-foreground">
                <button
                  type="button"
                  onClick={goToLogin}
                  className="text-accent hover:text-accent-hover font-medium transition-colors"
                >
                  Back to login
                </button>
              </p>
            </div>
          )}

          {flowState === "reset" && (
            <form onSubmit={handleResetSubmit} className="space-y-4">
              <div>
                <label htmlFor="new-password" className="label">New password</label>
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
                {isLoading ? "Saving..." : "Set password"}
              </button>

              <p className="text-center text-sm text-muted-foreground">
                <button
                  type="button"
                  onClick={goToLogin}
                  className="text-accent hover:text-accent-hover font-medium transition-colors"
                >
                  Back to login
                </button>
              </p>
            </form>
          )}

          {flowState === "login" && (
            <p className="mt-6 text-center text-sm text-muted-foreground">
              Don&apos;t have an account?{" "}
              <Link href="/register" className="text-accent hover:text-accent-hover font-medium transition-colors">
                Create one
              </Link>
            </p>
          )}
        </div>
      </div>
    </main>
  );
}
