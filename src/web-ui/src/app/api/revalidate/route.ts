import { revalidatePath } from "next/cache";

export async function POST(request: Request) {
  const { secret, paths } = await request.json();

  if (secret !== process.env.REVALIDATION_SECRET) {
    return Response.json({ error: "Invalid secret" }, { status: 401 });
  }

  for (const path of paths) {
    revalidatePath(path);
  }

  return Response.json({ revalidated: true });
}
