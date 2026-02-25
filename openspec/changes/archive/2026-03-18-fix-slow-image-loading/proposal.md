## Why

Project pages on naglasupan.is load slowly due to image loading bottlenecks. HAR analysis of a project detail page shows images don't start loading until 1180ms after navigation (blocked by JS hydration), and then the Next.js image optimizer takes 580-974ms per image even on cache HITs because 10 simultaneous requests queue on the server. Total time to last image: 2.2 seconds.

## What Changes

- Add `priority` prop to above-the-fold images (hero image on project detail, first 6 cards on project listing) so Next.js emits `<link rel="preload">` in the HTML head, allowing browsers to fetch images during JS download instead of after hydration
- Enable AVIF image format in Next.js config for 20-30% smaller files than WebP at similar quality
- Increase `minimumCacheTTL` to 30 days to reduce frequency of server-side re-optimization (currently 4 hours)

## Capabilities

### New Capabilities

_None — this is a performance optimization of existing image rendering._

### Modified Capabilities

_No existing specs to modify._

## Impact

- `src/web-ui/src/components/ImageUpload/ImageGallery.tsx` — add `priority` to main image
- `src/web-ui/src/app/projects/ProjectsListing.tsx` — add `priority` to first 6 visible cards
- `src/web-ui/next.config.ts` — add `formats` and `minimumCacheTTL` to images config
