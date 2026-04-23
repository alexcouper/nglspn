import "server-only";
import { cookies } from "next/headers";

export const EDIT_MODE_COOKIE = "nglspn-edit-mode";

export async function readEditModeFromServer(): Promise<boolean> {
  const store = await cookies();
  return store.get(EDIT_MODE_COOKIE)?.value === "1";
}
