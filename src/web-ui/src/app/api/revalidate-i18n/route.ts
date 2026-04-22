import { NextResponse } from "next/server";
import { revalidateTag } from "next/cache";
import { locales } from "@/i18n/config";

export async function POST(request: Request) {
  const secret = process.env.WEB_UI_REVALIDATE_SECRET;
  if (!secret) {
    return NextResponse.json(
      { error: "WEB_UI_REVALIDATE_SECRET not configured" },
      { status: 500 },
    );
  }

  const provided = request.headers.get("x-revalidate-secret");
  if (provided !== secret) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  let body: { locale?: unknown };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }

  const locale = body.locale;
  if (
    typeof locale !== "string" ||
    !(locales as readonly string[]).includes(locale)
  ) {
    return NextResponse.json({ error: "invalid locale" }, { status: 400 });
  }

  revalidateTag(`i18n:${locale}`, "max");
  return NextResponse.json({ revalidated: true, locale });
}
