import type { Element } from "hast";
import { GALLERY_CLASS, type GalleryImage } from "./gallery-mdast";

function classNames(element: Element): string[] {
  const value = element.properties?.className;
  if (Array.isArray(value)) return value.map(String);
  if (typeof value === "string") return value.split(/\s+/);
  return [];
}

function stringProperty(
  element: Element,
  name: string,
): string | undefined {
  const value = element.properties?.[name];
  return typeof value === "string" && value !== "" ? value : undefined;
}

/**
 * Pulls the images out of a rendered `<div class="gallery">`, or returns null
 * if the element is an ordinary div.
 *
 * Reads the hast node rather than the rendered React children: this runs
 * after sanitisation, so what it sees is what survived the allowlist, and
 * `src`/`alt` come off the node as plain strings rather than through React
 * element introspection.
 */
export function galleryImagesFromElement(
  element: Element | undefined,
): GalleryImage[] | null {
  if (!element || !classNames(element).includes(GALLERY_CLASS)) return null;

  const images: GalleryImage[] = [];
  for (const child of element.children) {
    if (child.type !== "element" || child.tagName !== "img") continue;
    const src = stringProperty(child, "src");
    if (!src) continue;
    images.push({
      src,
      alt: stringProperty(child, "alt") ?? "",
      ...(stringProperty(child, "title")
        ? { title: stringProperty(child, "title") }
        : {}),
    });
  }
  return images;
}
