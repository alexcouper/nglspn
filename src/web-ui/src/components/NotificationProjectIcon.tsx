"use client";

import { useState } from "react";

interface Props {
  imageUrl: string | null | undefined;
  title: string;
  size: number;
  className?: string;
}

const PALETTE = [
  "bg-rose-200 text-rose-700",
  "bg-amber-200 text-amber-700",
  "bg-emerald-200 text-emerald-700",
  "bg-sky-200 text-sky-700",
  "bg-violet-200 text-violet-700",
  "bg-pink-200 text-pink-700",
  "bg-teal-200 text-teal-700",
  "bg-indigo-200 text-indigo-700",
];

function pickPalette(seed: string): string {
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash * 31 + seed.charCodeAt(i)) | 0;
  }
  const index = Math.abs(hash) % PALETTE.length;
  return PALETTE[index];
}

export function NotificationProjectIcon({
  imageUrl,
  title,
  size,
  className = "",
}: Props) {
  const [errored, setErrored] = useState(false);
  const showImage = imageUrl && !errored;
  const initial = (title.trim().charAt(0) || "?").toUpperCase();
  const palette = pickPalette(title);

  return (
    <div
      style={{ width: size, height: size }}
      className={`flex-shrink-0 rounded overflow-hidden flex items-center justify-center ${
        showImage ? "bg-slate-100" : palette
      } ${className}`}
    >
      {showImage ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={imageUrl ?? undefined}
          alt=""
          width={size}
          height={size}
          className="w-full h-full object-cover"
          loading="lazy"
          onError={() => setErrored(true)}
        />
      ) : (
        <span
          className="font-semibold"
          style={{ fontSize: Math.max(12, Math.floor(size * 0.45)) }}
          aria-hidden="true"
        >
          {initial}
        </span>
      )}
    </div>
  );
}
