## 1. Next.js Image Config

- [x] 1.1 Add `formats: ["image/avif", "image/webp"]` to `images` config in `src/web-ui/next.config.ts`
- [x] 1.2 Add `minimumCacheTTL: 2592000` (30 days) to `images` config in `src/web-ui/next.config.ts`

## 2. Priority on Project Detail Page

- [x] 2.1 Add `priority` prop to the main hero image in `src/web-ui/src/components/ImageUpload/ImageGallery.tsx` (the `<Image>` inside the main image container, ~line 76)

## 3. Priority on Project Listing Page

- [x] 3.1 Add `priority` prop to `ProjectCard` component — accept it as a prop and pass through to `<Image>` in `src/web-ui/src/app/projects/ProjectsListing.tsx`
- [x] 3.2 Add `priority` prop to `CompetitionProjectCard` component — accept it as a prop and pass through to `<Image>` in `src/web-ui/src/app/projects/ProjectsListing.tsx`
- [x] 3.3 Pass `priority={index < 6}` when rendering `ProjectCard` and `CompetitionProjectCard` in the grid maps

## 4. Verification

- [x] 4.1 Run `cd src/web-ui && npm run lint` — passes
- [x] 4.2 Run `cd src/web-ui && npm run build` — builds without errors
