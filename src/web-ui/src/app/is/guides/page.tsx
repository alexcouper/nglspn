import { GuideIndex } from "@/components/guides/GuidePages";
import { guideMetadata } from "@/lib/guides";

export const metadata = guideMetadata("is");

export default function IcelandicGuidesPage() {
  return <GuideIndex language="is" />;
}
