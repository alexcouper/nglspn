"use client";

import { useState, useCallback } from "react";
import { XMarkIcon, TrashIcon } from "@heroicons/react/24/outline";
import { useTranslations } from "next-intl";
import type { Image, DiscoverProject } from "@/lib/api";
import { pickVariant } from "@/lib/utils";
import { LargeHeroCard } from "@/app/projects/sections/FeaturedSection";
import { ArrivalCard } from "@/app/projects/sections/NewArrivalsSection";
import { Dialog } from "@/components/Dialog";

interface ImageRoleDialogProps {
  image: Image;
  projectTitle: string;
  projectTagline: string;
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  onUpdateRoles: (
    imageId: string,
    roles: { is_main?: boolean; is_hero?: boolean; is_usage?: boolean }
  ) => void;
  onDelete: (imageId: string) => void;
}

interface RoleConfig {
  key: "is_main" | "is_hero" | "is_usage";
  // Message key under images.roleDialog.roles; label, description and
  // dimensions hang off it.
  name: "main" | "hero" | "usage";
}

const ROLES: RoleConfig[] = [
  { key: "is_main", name: "main" },
  { key: "is_hero", name: "hero" },
  { key: "is_usage", name: "usage" },
];

export function ImageRoleDialog({
  image,
  projectTitle,
  projectTagline,
  projectId,
  isOpen,
  onClose,
  onUpdateRoles,
  onDelete,
}: ImageRoleDialogProps) {
  const t = useTranslations("images.roleDialog");
  const [confirmDelete, setConfirmDelete] = useState(false);

  const roles = {
    is_main: image.is_main,
    is_hero: image.is_hero,
    is_usage: image.is_usage,
  };

  const handleToggle = useCallback(
    (key: "is_main" | "is_hero" | "is_usage") => {
      onUpdateRoles(image.id, { [key]: !image[key] });
    },
    [image, onUpdateRoles]
  );

  const handleDelete = useCallback(() => {
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    onDelete(image.id);
    onClose();
  }, [confirmDelete, image.id, onDelete, onClose]);

  const imageUrl =
    pickVariant(image.variants, "medium") ?? image.url;

  const previewProject: DiscoverProject = {
    id: projectId,
    slug: null,
    title: projectTitle || t("untitledProject"),
    tagline: projectTagline || "",
    icon_url: null,
    hero_banner_url: imageUrl,
    in_use_image_url: imageUrl,
    category_name: null,
    category_slug: null,
    discussion_count: 0,
    won_competitions: [],
    is_community_tipoff: false,
  };

  return (
    <Dialog isOpen={isOpen} onClose={onClose} className="max-w-2xl max-h-[90vh] overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between -mt-2 mb-4">
        <h2 className="text-lg font-semibold text-foreground">
          {t("title")}
        </h2>
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-muted transition-colors -mr-2"
        >
          <XMarkIcon className="w-5 h-5" />
        </button>
      </div>

      <div className="space-y-6">
        {/* Selected image preview */}
        <div className="rounded-lg overflow-hidden bg-muted">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={imageUrl}
            alt={image.original_filename}
            className="w-full h-auto max-h-48 object-contain"
          />
        </div>

        {/* Role toggles with previews */}
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-foreground">
            {t("displayRoles")}
          </h3>

          {ROLES.map((role) => (
            <div key={role.key} className="space-y-2">
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={roles[role.key]}
                  onChange={() => handleToggle(role.key)}
                  className="mt-1 h-4 w-4 rounded border-border text-accent focus:ring-accent"
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-foreground">
                      {t(`roles.${role.name}.label`)}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {t(`roles.${role.name}.dimensions`)}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {t(`roles.${role.name}.description`)}
                  </p>
                </div>
              </label>

              {/* Live preview */}
              <div className="ml-7 rounded-lg overflow-hidden border border-border bg-muted/50">
                {role.key === "is_main" && (
                  <div className="p-2">
                    <div className="rounded-lg overflow-hidden bg-muted max-w-[280px]">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={imageUrl}
                        alt={t("mainPreviewAlt")}
                        className="w-full h-auto object-contain"
                      />
                    </div>
                    <p className="text-[10px] text-muted-foreground mt-1">
                      {t("mainPreviewCaption")}
                    </p>
                  </div>
                )}
                {role.key === "is_hero" && (
                  <div className="p-2">
                    <div className="max-w-[320px] pointer-events-none">
                      <LargeHeroCard project={previewProject} />
                    </div>
                  </div>
                )}
                {role.key === "is_usage" && (
                  <div className="p-2">
                    <div className="max-w-[240px] pointer-events-none">
                      <ArrivalCard project={previewProject} />
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Delete */}
        <div className="pt-2 border-t border-border">
          <button
            onClick={handleDelete}
            className={`flex items-center gap-2 px-3 py-2 rounded text-sm transition-colors ${
              confirmDelete
                ? "bg-red-500 text-white hover:bg-red-600"
                : "text-red-500 hover:bg-red-50"
            }`}
          >
            <TrashIcon className="w-4 h-4" />
            {confirmDelete ? t("confirmDelete") : t("deleteImage")}
          </button>
        </div>
      </div>
    </Dialog>
  );
}
