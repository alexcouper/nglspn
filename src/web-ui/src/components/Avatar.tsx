import { getAuthorName } from "@/lib/utils";

interface AvatarProps {
  src: string | null | undefined;
  firstName: string;
  lastName: string;
  // Diameter in px. Text scales with it.
  size: number;
  className?: string;
}

// The first letter of each non-empty name. Empty when there is no name to take
// a letter from, which the component turns into a glyph.
export function initialsFor(firstName: string, lastName: string): string {
  return [firstName, lastName]
    .map((name) => name.trim())
    .filter(Boolean)
    .map((name) => name[0].toLocaleUpperCase())
    .join("");
}

// The one place an avatar is drawn: the profile header, the edit page and the
// nav's account button. Without an image it falls back to initials in the
// accent tint, and without a name to a person glyph, so a slot is never empty.
export function Avatar({ src, firstName, lastName, size, className = "" }: AvatarProps) {
  const name = getAuthorName({ first_name: firstName, last_name: lastName });
  const box = { width: size, height: size };

  if (src) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={src}
        alt={name}
        width={size}
        height={size}
        style={box}
        className={`rounded-full object-cover shrink-0 ${className}`}
      />
    );
  }

  const initials = initialsFor(firstName, lastName);

  return (
    <span
      role="img"
      aria-label={name}
      style={{ ...box, fontSize: Math.round(size / 3) }}
      className={`inline-flex items-center justify-center rounded-full bg-accent-subtle text-indigo-700 font-semibold tracking-tight shrink-0 select-none ${className}`}
    >
      {initials ? (
        <span aria-hidden="true">{initials}</span>
      ) : (
        <svg
          aria-hidden="true"
          style={{ width: size / 2, height: size / 2 }}
          fill="none"
          stroke="currentColor"
          strokeWidth={1.5}
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.5 20.1a7.5 7.5 0 0 1 15 0A17.9 17.9 0 0 1 12 21.75c-2.68 0-5.22-.58-7.5-1.65Z"
          />
        </svg>
      )}
    </span>
  );
}
