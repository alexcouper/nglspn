import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/contexts/auth";
import { buildLoginPath } from "@/lib/auth-routing";
import { api } from "@/lib/api";

export function useRequireAuth() {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading, user } = useAuth();

  useEffect(() => {
    if (!isLoading && !isAuthenticated && !api.isAuthenticated()) {
      router.push(buildLoginPath(pathname));
      return;
    }
    if (
      !isLoading &&
      user &&
      user.pending_onboarding_steps.length > 0 &&
      pathname !== "/onboarding"
    ) {
      router.push("/onboarding");
    }
  }, [isLoading, isAuthenticated, user, pathname, router]);

  return {
    isReady: isAuthenticated || api.isAuthenticated(),
    isLoading,
  };
}
