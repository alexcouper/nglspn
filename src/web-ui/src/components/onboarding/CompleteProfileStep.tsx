"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { Translatable } from "@/components/Translatable";

interface CompleteProfileStepProps {
  onComplete: () => void;
}

export function CompleteProfileStep({ onComplete }: CompleteProfileStepProps) {
  const t = useTranslations();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  const hasAtLeastOneName = firstName.trim() !== "" || lastName.trim() !== "";

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!hasAtLeastOneName) return;

      setError("");
      setIsSaving(true);

      try {
        await api.auth.updateCurrentUser({
          first_name: firstName,
          last_name: lastName,
        });
        onComplete();
      } catch (err) {
        setError(err instanceof Error ? err.message : t("error.saveFailed"));
      } finally {
        setIsSaving(false);
      }
    },
    [firstName, lastName, hasAtLeastOneName, onComplete, t]
  );

  return (
    <>
      <div className="text-center mb-8">
        <h1 className="text-2xl font-semibold text-foreground tracking-tight">
          <Translatable tKey="onboarding.completeProfile.heading">{t("onboarding.completeProfile.heading")}</Translatable>
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          <Translatable tKey="onboarding.completeProfile.subheading">{t("onboarding.completeProfile.subheading")}</Translatable>
        </p>
      </div>

      <div className="bg-white border border-border rounded-xl p-6 shadow-sm">
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2.5 rounded-lg text-sm text-center">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="firstName" className="label">
              <Translatable tKey="onboarding.completeProfile.firstNameLabel">{t("onboarding.completeProfile.firstNameLabel")}</Translatable>
            </label>
            <input
              type="text"
              id="firstName"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              className="input"
              placeholder={t("onboarding.completeProfile.firstNamePlaceholder")}
              autoFocus
            />
          </div>

          <div>
            <label htmlFor="lastName" className="label">
              <Translatable tKey="onboarding.completeProfile.lastNameLabel">{t("onboarding.completeProfile.lastNameLabel")}</Translatable>
            </label>
            <input
              type="text"
              id="lastName"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              className="input"
              placeholder={t("onboarding.completeProfile.lastNamePlaceholder")}
            />
          </div>

          <button
            type="submit"
            disabled={!hasAtLeastOneName || isSaving}
            className="btn-primary w-full py-2.5"
          >
            {isSaving ? (
              <Translatable tKey="onboarding.completeProfile.submitting">{t("onboarding.completeProfile.submitting")}</Translatable>
            ) : (
              <Translatable tKey="onboarding.completeProfile.submit">{t("onboarding.completeProfile.submit")}</Translatable>
            )}
          </button>
        </form>
      </div>
    </>
  );
}
