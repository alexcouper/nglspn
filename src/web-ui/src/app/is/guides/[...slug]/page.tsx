import { notFound } from "next/navigation";
import { GuideArticle } from "@/components/guides/GuidePages";
import { icelandicGuides } from "@/content/guides-is";
import { guideMetadata, localizedGuide } from "@/lib/guides";

export const dynamicParams = false;

export function generateStaticParams() {
  return icelandicGuides.map((guide) => ({ slug: guide.slug.split("/") }));
}

type Props = { params: Promise<{ slug: string[] }> };

export async function generateMetadata({ params }: Props) {
  const guide = localizedGuide("is", (await params).slug.join("/"));
  if (!guide) notFound();
  return guideMetadata("is", guide);
}

export default async function IcelandicGuidePage({ params }: Props) {
  const guide = localizedGuide("is", (await params).slug.join("/"));
  if (!guide) notFound();
  return <GuideArticle guide={guide} language="is" />;
}
