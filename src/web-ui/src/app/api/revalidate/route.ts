import { revalidatePath } from "next/cache";

export async function POST(request: Request) {
  let body;
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { secret, paths } = body;

  if (typeof secret !== "string" || secret !== process.env.REVALIDATION_SECRET) {
    return Response.json({ error: "Invalid secret" }, { status: 401 });
  }

  if (
    !Array.isArray(paths) ||
    paths.length === 0 ||
    paths.length > 50 ||
    !paths.every((p: unknown) => typeof p === "string")
  ) {
    return Response.json(
      { error: "paths must be an array of 1-50 strings" },
      { status: 400 }
    );
  }

  for (const path of paths) {
    revalidatePath(path);
  }

  return Response.json({ revalidated: true });
}
