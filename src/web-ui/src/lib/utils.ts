export const PLACEHOLDER_COLORS = [
  "bg-rose-200",
  "bg-amber-200",
  "bg-lime-200",
  "bg-teal-200",
  "bg-sky-200",
  "bg-violet-200",
  "bg-pink-200",
  "bg-orange-200",
];

export function getPlaceholderColor(id: string): string {
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = (hash << 5) - hash + id.charCodeAt(i);
    hash |= 0;
  }
  return PLACEHOLDER_COLORS[Math.abs(hash) % PLACEHOLDER_COLORS.length];
}

type ImageVariant = { size: string; url: string; width: number; height: number };

const VARIANT_SIZE_ORDER = ["thumb", "medium", "large"] as const;

/**
 * Pick the best available variant for a rendering context.
 * Prefers the requested size, then falls up to larger sizes.
 * Returns the variant URL, or null if no suitable variant exists.
 */
export function pickVariant(
  variants: ImageVariant[] | undefined,
  preferred: string
): string | null {
  if (!variants || variants.length === 0) return null;

  const startIndex = VARIANT_SIZE_ORDER.indexOf(
    preferred as (typeof VARIANT_SIZE_ORDER)[number]
  );
  if (startIndex === -1) return null;

  for (let i = startIndex; i < VARIANT_SIZE_ORDER.length; i++) {
    const match = variants.find((v) => v.size === VARIANT_SIZE_ORDER[i]);
    if (match) return match.url;
  }

  return null;
}

export function getContrastColor(hexColor: string): string {
  const hex = hexColor.replace("#", "");
  const r = parseInt(hex.substring(0, 2), 16);
  const g = parseInt(hex.substring(2, 4), 16);
  const b = parseInt(hex.substring(4, 6), 16);
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.5 ? "#000000" : "#ffffff";
}
