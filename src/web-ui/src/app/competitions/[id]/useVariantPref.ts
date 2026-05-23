import { useState } from "react";

export type RankingVariant = "L" | "R";

const STORAGE_KEY = "ranking-variant-pref";

function isValidVariant(value: string | null): value is RankingVariant {
  return value === "L" || value === "R";
}

interface UseVariantPrefInput {
  /** The current location.search string, e.g. "?variants=on". Injectable for tests. */
  search?: string;
}

export function useVariantPref(
  input: UseVariantPrefInput = {}
): {
  variant: RankingVariant;
  setVariant: (next: RankingVariant) => void;
  toggleEnabled: boolean;
} {
  const search =
    input.search ??
    (typeof window === "undefined" ? "" : window.location.search);

  const toggleEnabled = new URLSearchParams(search).get("variants") === "on";

  const [variant, setVariantState] = useState<RankingVariant>(() => {
    if (!toggleEnabled) return "L";
    if (typeof window === "undefined") return "L";
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return isValidVariant(stored) ? stored : "L";
  });

  // If the toggle is disabled we never persist anything.
  const setVariant = (next: RankingVariant) => {
    setVariantState(next);
    if (toggleEnabled && typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, next);
    }
  };

  return { variant, setVariant, toggleEnabled };
}
