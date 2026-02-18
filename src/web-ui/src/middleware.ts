import { NextRequest, NextResponse } from "next/server";

const CANONICAL_DOMAIN = "naglasupan.is";
const IDN_DOMAIN = "xn--naglaspan-b9a.is";

export function middleware(request: NextRequest) {
  const host = request.headers.get("host")?.split(":")[0];

  if (host === IDN_DOMAIN) {
    const url = request.nextUrl.clone();
    url.host = CANONICAL_DOMAIN;
    url.port = "";
    return NextResponse.redirect(url, 301);
  }
}
