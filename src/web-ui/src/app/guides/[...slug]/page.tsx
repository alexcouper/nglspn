import { notFound } from "next/navigation";
import { GuideArticle } from "@/components/guides/GuidePages";
import { guidesFor } from "@/content/guides";
import { guideMetadata, localizedGuide } from "@/lib/guides";

export const dynamicParams = false;

export function generateStaticParams() {
  return guidesFor("en").map((guide) => ({ slug: guide.slug.split("/") }));
}

type Props = { params: Promise<{ slug: string[] }> };

export async function generateMetadata({ params }: Props) {
  const guide = localizedGuide("en", (await params).slug.join("/"));
  if (!guide) notFound();
  return guideMetadata("en", guide);
}

export default async function GuidePage({ params }: Props) {
  const guide = localizedGuide("en", (await params).slug.join("/"));
  if (!guide) notFound();
  return <GuideArticle guide={guide} language="en" />;
}
