import { beforeEach, describe, expect, it } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useVariantPref } from "./useVariantPref";

describe("useVariantPref", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("returns default variant L and toggleEnabled=false when ?variants is absent", () => {
    const { result } = renderHook(() =>
      useVariantPref({ search: "" })
    );
    expect(result.current.variant).toBe("L");
    expect(result.current.toggleEnabled).toBe(false);
  });

  it("enables the toggle when ?variants=on is present", () => {
    const { result } = renderHook(() =>
      useVariantPref({ search: "?variants=on" })
    );
    expect(result.current.toggleEnabled).toBe(true);
  });

  it("reads persisted preference from localStorage when toggle is enabled", () => {
    localStorage.setItem("ranking-variant-pref", "R");
    const { result } = renderHook(() =>
      useVariantPref({ search: "?variants=on" })
    );
    expect(result.current.variant).toBe("R");
  });

  it("ignores invalid persisted values", () => {
    localStorage.setItem("ranking-variant-pref", "bogus");
    const { result } = renderHook(() =>
      useVariantPref({ search: "?variants=on" })
    );
    expect(result.current.variant).toBe("L");
  });

  it("writes the new variant to localStorage on set", () => {
    const { result } = renderHook(() =>
      useVariantPref({ search: "?variants=on" })
    );
    act(() => {
      result.current.setVariant("R");
    });
    expect(result.current.variant).toBe("R");
    expect(localStorage.getItem("ranking-variant-pref")).toBe("R");
  });
});
