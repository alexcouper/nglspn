import type { Locale } from "@/i18n/config";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.API_URL ||
  "http://localhost:8000";

export type TranslationAuditEntry = {
  changed_at: string;
  changed_by: string | null;
  old_text: string;
  new_text: string;
};

export type TranslationDetail = {
  locale: string;
  key: string;
  text: string;
  updated_at: string | null;
  history: TranslationAuditEntry[];
};

export type TranslationPatchResponse = {
  locale: string;
  key: string;
  text: string;
  source_hash: string;
  is_machine_translated: boolean;
  updated_at: string;
};

export async function getTranslationDetail(
  locale: Locale,
  key: string,
): Promise<TranslationDetail> {
  const url = `${API_URL}/api/i18n/${locale}/${encodeURIComponent(key)}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`getTranslationDetail ${locale}/${key}: ${res.status}`);
  }
  return (await res.json()) as TranslationDetail;
}

export async function patchTranslation(
  locale: Locale,
  key: string,
  text: string,
  bearerToken: string,
): Promise<TranslationPatchResponse> {
  const url = `${API_URL}/api/i18n/${locale}/${encodeURIComponent(key)}`;
  const res = await fetch(url, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${bearerToken}`,
    },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`patchTranslation ${locale}/${key}: ${res.status} ${detail}`);
  }
  return (await res.json()) as TranslationPatchResponse;
}
