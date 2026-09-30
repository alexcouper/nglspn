import { GuideIndex } from "@/components/guides/GuidePages";
import { guideMetadata } from "@/lib/guides";

export const metadata = guideMetadata("en");

export default function GuidesPage() {
  return <GuideIndex language="en" />;
}
