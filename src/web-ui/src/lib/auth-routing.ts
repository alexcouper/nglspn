import type { User } from "@/lib/api";

export function getPostAuthDestination(user: User): string {
  if (!user.is_verified) {
    return "/verify-email";
  }
  // Future: add phone verification, onboarding, etc.
  return "/my-projects";
}
