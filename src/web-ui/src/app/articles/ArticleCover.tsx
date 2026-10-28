"use client";

import { type CropRect, CroppedImage } from "@/components/CroppedImage";

interface Props {
  src: string;
  crop: CropRect | null | undefined;
  priority?: boolean;
}

// The listing image shown wide at the top of an article. One component for the
// rendered page and the editor's cover slot, so what the author sees while
// writing is framed the way readers will get it.
export function ArticleCover({ src, crop, priority = false }: Props) {
  return (
    <div className="max-w-[52rem] mx-auto rounded-lg sm:rounded-xl overflow-hidden">
      <CroppedImage
        src={src}
        alt=""
        crop={crop}
        priority={priority}
        testId="article-listing-image"
      />
    </div>
  );
}
