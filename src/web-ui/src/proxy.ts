import { NextRequest, NextResponse } from "next/server";

const CANONICAL_DOMAIN = "naglasupan.is";
const IDN_DOMAIN = "xn--naglaspan-b9a.is";

const PROTECTED_ROUTES = ["/submit", "/profile", "/my-projects", "/my-reviews"];

export function proxy(request: NextRequest) {
  const host = request.headers.get("host")?.split(":")[0];

  if (host === IDN_DOMAIN) {
    const url = request.nextUrl.clone();
    url.host = CANONICAL_DOMAIN;
    url.port = "";
    return NextResponse.redirect(url, 301);
  }

  const { pathname, searchParams } = request.nextUrl;

  // --- Maintenance bypass (server-side) ---
  const bypassSecret = process.env.MAINTENANCE_BYPASS_SECRET;
  if (bypassSecret) {
    const queryBypass = searchParams.get("bypass_maintenance");
    if (queryBypass === bypassSecret) {
      // Set cookie and redirect to strip the query parameter
      const url = request.nextUrl.clone();
      url.searchParams.delete("bypass_maintenance");
      const response = NextResponse.redirect(url);
      response.cookies.set("maintenance_bypass", bypassSecret, {
        path: "/",
        httpOnly: true,
        sameSite: "lax",
        secure: process.env.NODE_ENV === "production",
      });
      return response;
    }
  }

  // --- Client-side route protection ---
  const isProtected = PROTECTED_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(route + "/")
  );
  if (isProtected) {
    const loggedIn = request.cookies.get("logged_in");
    if (!loggedIn) {
      const loginUrl = request.nextUrl.clone();
      loginUrl.pathname = "/login";
      return NextResponse.redirect(loginUrl);
    }
  }
}
