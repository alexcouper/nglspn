import "server-only";
import { unstable_cache } from "next/cache";
import type { Locale } from "@/i18n/config";

const API_URL =
  process.env.API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

export type Catalog = Record<string, string>;

async function fetchCatalogFresh(locale: Locale): Promise<Catalog> {
  const res = await fetch(`${API_URL}/api/i18n/${locale}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    console.warn(`[i18n] Failed to load catalog for ${locale}: ${res.status}`);
    return {};
  }
  return (await res.json()) as Catalog;
}

export const fetchCatalog = (locale: Locale): Promise<Catalog> =>
  unstable_cache(
    () => fetchCatalogFresh(locale),
    ["i18n", locale],
    { tags: [`i18n:${locale}`], revalidate: 60 },
  )();
