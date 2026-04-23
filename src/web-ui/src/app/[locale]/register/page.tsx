"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useAuth } from "@/contexts/auth";
import { getPostAuthDestination } from "@/lib/auth-routing";
import { Translatable } from "@/components/Translatable";

export default function RegisterPage() {
  const t = useTranslations();
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next");
  const { register } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [kennitala, setKennitala] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError(t("auth.register.passwordTooShort"));
      return;
    }

    if (!/^\d{10}$/.test(kennitala)) {
      setError(t("auth.register.kennitalaInvalid"));
      return;
    }

    setIsLoading(true);

    try {
      const userData = await register(email, password, kennitala);
      router.push(getPostAuthDestination(userData, next));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error.registrationFailed"));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-muted flex items-center justify-center px-4 pt-14">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-semibold text-foreground tracking-tight">
            <Translatable tKey="auth.register.heading">{t("auth.register.heading")}</Translatable>
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            <Translatable tKey="auth.register.subheading">{t("auth.register.subheading")}</Translatable>
          </p>
        </div>

        <div className="bg-white border border-border rounded-xl p-6 shadow-sm">
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2.5 rounded-lg text-sm">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="email" className="label">
                <Translatable tKey="auth.register.emailLabel">{t("auth.register.emailLabel")}</Translatable>
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
                placeholder={t("auth.register.emailPlaceholder")}
              />
            </div>

            <div>
              <label htmlFor="password" className="label">
                <Translatable tKey="auth.register.passwordLabel">{t("auth.register.passwordLabel")}</Translatable>
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="new-password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input"
                placeholder={t("auth.register.passwordPlaceholder")}
              />
            </div>

            <div>
              <label htmlFor="kennitala" className="label">
                <Translatable tKey="auth.register.kennitalaLabel">{t("auth.register.kennitalaLabel")}</Translatable>
              </label>
              <input
                id="kennitala"
                name="kennitala"
                type="text"
                required
                maxLength={10}
                value={kennitala}
                onChange={(e) => setKennitala(e.target.value.replace(/\D/g, ""))}
                className="input"
                placeholder={t("auth.register.kennitalaPlaceholder")}
              />
            </div>

            <p className="text-xs text-muted-foreground">
              <Translatable tKey="auth.register.privacyAgreement">{t("auth.register.privacyAgreement")}</Translatable>{" "}
              <Link href="/privacy" className="text-accent hover:text-accent-hover transition-colors">
                <Translatable tKey="auth.register.privacyLink">{t("auth.register.privacyLink")}</Translatable>
              </Link>.
            </p>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full btn-primary py-2.5"
            >
              {isLoading ? (
                <Translatable tKey="auth.register.submitting">{t("auth.register.submitting")}</Translatable>
              ) : (
                <Translatable tKey="auth.register.submit">{t("auth.register.submit")}</Translatable>
              )}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-muted-foreground">
            <Translatable tKey="auth.register.haveAccount">{t("auth.register.haveAccount")}</Translatable>{" "}
            <Link href={next ? `/login?next=${encodeURIComponent(next)}` : "/login"} className="text-accent hover:text-accent-hover font-medium transition-colors">
              <Translatable tKey="auth.register.loginLink">{t("auth.register.loginLink")}</Translatable>
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
