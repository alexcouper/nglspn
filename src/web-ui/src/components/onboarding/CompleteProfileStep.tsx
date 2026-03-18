"use client";

import { useState, useCallback } from "react";
import { api } from "@/lib/api";

interface CompleteProfileStepProps {
  onComplete: () => void;
}

export function CompleteProfileStep({ onComplete }: CompleteProfileStepProps) {
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
        setError(err instanceof Error ? err.message : "Failed to save. Please try again.");
      } finally {
        setIsSaving(false);
      }
    },
    [firstName, lastName, hasAtLeastOneName, onComplete]
  );

  return (
    <>
      <div className="text-center mb-8">
        <h1 className="text-2xl font-semibold text-foreground tracking-tight">
          Complete your profile
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Add your name so others know who you are
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
              First Name
            </label>
            <input
              type="text"
              id="firstName"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              className="input"
              placeholder="Your first name"
              autoFocus
            />
          </div>

          <div>
            <label htmlFor="lastName" className="label">
              Last Name
            </label>
            <input
              type="text"
              id="lastName"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              className="input"
              placeholder="Your last name"
            />
          </div>

          <button
            type="submit"
            disabled={!hasAtLeastOneName || isSaving}
            className="btn-primary w-full py-2.5"
          >
            {isSaving ? "Saving..." : "Continue"}
          </button>
        </form>
      </div>
    </>
  );
}
