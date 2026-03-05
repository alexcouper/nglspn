import { NextRequest, NextResponse } from "next/server";

const CANONICAL_DOMAIN = "naglasupan.is";
const IDN_DOMAIN = "xn--naglaspan-b9a.is";

export function proxy(request: NextRequest) {
  const host = request.headers.get("host")?.split(":")[0];

  if (host === IDN_DOMAIN) {
    const url = request.nextUrl.clone();
    url.host = CANONICAL_DOMAIN;
    url.port = "";
    return NextResponse.redirect(url, 301);
  }

  const { searchParams } = request.nextUrl;

  // --- Maintenance bypass (server-side) ---
  const bypassSecret = process.env.MAINTENANCE_BYPASS_SECRET;
  if (bypassSecret) {
    const queryBypass = searchParams.get("bypass_maintenance");
    if (queryBypass === bypassSecret) {
      const url = request.nextUrl.clone();
      url.searchParams.delete("bypass_maintenance");
      const response = NextResponse.redirect(url);
      response.cookies.set("maintenance_bypass", bypassSecret, {
        path: "/",
        sameSite: "lax",
        secure: process.env.NODE_ENV === "production",
      });
      return response;
    }

    const bypassCookie = request.cookies.get("maintenance_bypass");
    if (bypassCookie && bypassCookie.value !== bypassSecret) {
      const response = NextResponse.next();
      response.cookies.delete("maintenance_bypass");
      return response;
    }
  }
}
