"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRightIcon, CameraIcon } from "@heroicons/react/24/outline";
import { ArrowPathIcon } from "@heroicons/react/24/solid";
import { useAuth } from "@/contexts/auth";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { api } from "@/lib/api";
import { describeApiError } from "@/lib/api/errors";
import {
  NotAnImageError,
  loadImageFile,
  renderAvatarBlob,
  type LoadedImage,
} from "@/lib/avatarBlob";
import { uploadAvatar } from "@/lib/avatarUpload";
import { Avatar } from "@/components/Avatar";
import type { CropRect } from "@/components/CroppedImage";
import { Dialog } from "@/components/Dialog";
import { ImageCropper } from "@/components/ImageCropper";
import { ProfileAbout } from "@/components/ProfileAbout";

export interface ProfileFormData {
  first_name: string;
  last_name: string;
  info: string;
}

const AVATAR_ACCEPT = "image/jpeg,image/png,image/webp";
const CROP_TITLE_ID = "avatar-crop-title";

interface Framing {
  source: LoadedImage;
  crop: CropRect | null;
}

// The profile editor: the public fields and nothing else. Account settings are
// at /profile/settings. Save returns to the public page, which is the preview.
export default function ProfilePage() {
  const router = useRouter();
  const { isLoading: authLoading } = useRequireAuth();
  const { user, isAuthenticated, refreshUser } = useAuth();

  const [formData, setFormData] = useState<ProfileFormData | null>(null);
  const [aboutMode, setAboutMode] = useState<"write" | "preview">("write");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  // The avatar saves on its own, on completion — it is an upload with a
  // progress state, not a form field, and tying it to Save would mean holding
  // a finished upload in limbo.
  const [framing, setFraming] = useState<Framing | null>(null);
  const [avatarBusy, setAvatarBusy] = useState(false);
  const [avatarError, setAvatarError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (user && !formData) {
      setFormData({
        first_name: user.first_name || "",
        last_name: user.last_name || "",
        info: user.info || "",
      });
    }
  }, [user, formData]);

  const setField = useCallback((field: keyof ProfileFormData, value: string) => {
    setFormData((prev) => (prev ? { ...prev, [field]: value } : prev));
  }, []);

  const publicPath = user ? `/users/${user.id}` : "/";

  const handleSave = async () => {
    if (!formData || !user) return;
    if (!formData.first_name.trim() && !formData.last_name.trim()) {
      setError("At least one name (first or last) is required");
      return;
    }
    setIsSaving(true);
    setError("");
    try {
      await api.auth.updateCurrentUser({
        first_name: formData.first_name,
        last_name: formData.last_name,
        info: formData.info,
      });
      await refreshUser();
      router.push(publicPath);
    } catch (err) {
      setError(describeApiError(err, "Couldn't save your profile."));
      setIsSaving(false);
    }
  };

  const handleFilePicked = async (file: File | undefined) => {
    if (!file) return;
    setAvatarError("");
    try {
      const source = await loadImageFile(file);
      setFraming({ source, crop: null });
    } catch (err) {
      setAvatarError(
        err instanceof NotAnImageError ? err.message : "Couldn't read that file.",
      );
    } finally {
      // So picking the same file again still fires onChange.
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleCropConfirmed = async () => {
    if (!framing) return;
    const { source, crop } = framing;
    setFraming(null);
    setAvatarBusy(true);
    setAvatarError("");
    try {
      const blob = await renderAvatarBlob(
        source,
        crop ?? { x: 0, y: 0, w: 1, h: source.height / source.width, ratio: 1 },
      );
      await uploadAvatar(blob);
      await refreshUser();
    } catch (err) {
      setAvatarError(describeApiError(err, "Couldn't upload that photo."));
    } finally {
      setAvatarBusy(false);
    }
  };

  const handleRemoveAvatar = async () => {
    setAvatarBusy(true);
    setAvatarError("");
    try {
      await api.auth.removeAvatar();
      await refreshUser();
    } catch (err) {
      setAvatarError(describeApiError(err, "Couldn't remove the photo."));
    } finally {
      setAvatarBusy(false);
    }
  };

  if (authLoading || !isAuthenticated || !user || !formData) {
    return (
      <main className="min-h-screen bg-muted pt-14">
        <section className="bg-white border-b border-border py-10 px-4 sm:px-6">
          <div className="max-w-2xl mx-auto flex items-center gap-6">
            <div className="skeleton h-24 w-24 rounded-full" />
            <div className="skeleton h-8 w-40" />
          </div>
        </section>
        <section className="py-8 px-4 sm:px-6">
          <div className="max-w-2xl mx-auto bg-white rounded-xl border border-border p-6">
            <div className="skeleton h-10 w-full mb-3" />
            <div className="skeleton h-10 w-full mb-3" />
            <div className="skeleton h-40 w-full" />
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-muted pt-14">
      <section className="bg-white border-b border-border py-8 sm:py-10 px-4 sm:px-6">
        <div className="max-w-2xl mx-auto flex flex-col sm:flex-row sm:items-center sm:justify-between gap-5">
          <div className="flex items-center gap-5 min-w-0">
            <div className="relative shrink-0">
              <Avatar
                src={user.avatar_url}
                firstName={formData.first_name}
                lastName={formData.last_name}
                size={96}
                className={avatarBusy ? "opacity-50" : ""}
              />
              <button
                type="button"
                aria-label="Change photo"
                disabled={avatarBusy}
                onClick={() => fileInputRef.current?.click()}
                className="absolute -right-1 -bottom-1 w-11 h-11 rounded-full bg-white border border-border shadow-sm flex items-center justify-center text-foreground hover:bg-muted disabled:opacity-50"
              >
                {avatarBusy ? (
                  <ArrowPathIcon className="w-4 h-4 animate-spin" />
                ) : (
                  <CameraIcon className="w-[18px] h-[18px]" />
                )}
              </button>
            </div>
            <div className="min-w-0">
              <h1 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight">
                Edit profile
              </h1>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-2">
                <label
                  htmlFor="avatar-file"
                  className="btn-secondary !py-1.5 !px-3.5 text-sm cursor-pointer"
                >
                  Upload photo
                </label>
                <input
                  ref={fileInputRef}
                  id="avatar-file"
                  type="file"
                  accept={AVATAR_ACCEPT}
                  className="sr-only"
                  disabled={avatarBusy}
                  onChange={(e) => handleFilePicked(e.target.files?.[0])}
                />
                {user.avatar_url && (
                  <button
                    type="button"
                    onClick={handleRemoveAvatar}
                    disabled={avatarBusy}
                    className="btn-ghost text-sm"
                  >
                    Remove
                  </button>
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-1.5">
                JPG, PNG or WebP. You will be asked to frame it as a square.
              </p>
              {avatarError && (
                <p className="text-xs text-red-600 mt-1.5" role="alert">
                  {avatarError}
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link href={publicPath} className="btn-secondary flex-1 sm:flex-none">
              Cancel
            </Link>
            <button
              type="button"
              onClick={handleSave}
              disabled={isSaving}
              className="btn-primary flex-1 sm:flex-none"
            >
              {isSaving ? <ArrowPathIcon className="w-4 h-4 animate-spin" /> : "Save changes"}
            </button>
          </div>
        </div>
      </section>

      <section className="py-8 px-4 sm:px-6">
        <div className="max-w-2xl mx-auto space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm" role="alert">
              {error}
            </div>
          )}

          <form
            className="bg-white rounded-xl border border-border p-6 space-y-5"
            onSubmit={(e) => {
              e.preventDefault();
              void handleSave();
            }}
          >
            <div>
              <h2 className="text-base font-semibold text-foreground tracking-tight">
                Name and about
              </h2>
              <p className="text-[13px] text-muted-foreground mt-1">
                Shown on your public profile and linked from every project you
                contribute to. Your projects and articles are listed there automatically.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="firstName" className="label">First name</label>
                <input
                  type="text"
                  id="firstName"
                  value={formData.first_name}
                  onChange={(e) => setField("first_name", e.target.value)}
                  className="input"
                  autoComplete="given-name"
                />
              </div>
              <div>
                <label htmlFor="lastName" className="label">Last name</label>
                <input
                  type="text"
                  id="lastName"
                  value={formData.last_name}
                  onChange={(e) => setField("last_name", e.target.value)}
                  className="input"
                  autoComplete="family-name"
                />
              </div>
            </div>
            <p className="text-xs text-muted-foreground -mt-2">At least one of the two is required.</p>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label htmlFor="info" className="label mb-0">About</label>
                <div
                  role="tablist"
                  aria-label="About editor mode"
                  className="flex rounded-lg border border-border overflow-hidden"
                >
                  {(["write", "preview"] as const).map((mode) => (
                    <button
                      key={mode}
                      type="button"
                      role="tab"
                      aria-selected={aboutMode === mode}
                      onClick={() => setAboutMode(mode)}
                      className={`px-3.5 py-1.5 text-xs font-medium transition-colors ${
                        aboutMode === mode
                          ? "bg-accent text-white"
                          : "bg-white text-muted-foreground hover:bg-muted hover:text-foreground"
                      }`}
                    >
                      {mode === "write" ? "Write" : "Preview"}
                    </button>
                  ))}
                </div>
              </div>
              {aboutMode === "write" ? (
                <textarea
                  id="info"
                  rows={11}
                  value={formData.info}
                  onChange={(e) => setField("info", e.target.value)}
                  className="input resize-none"
                  placeholder="Tell us about yourself..."
                />
              ) : (
                <div
                  className="rounded-lg border border-border bg-muted/40 px-4 py-3 min-h-[11rem]"
                  data-testid="about-preview"
                >
                  <ProfileAbout info={formData.info} emptyText="Nothing to preview yet." />
                </div>
              )}
              <div className="flex items-center justify-between mt-1.5">
                <p className="text-xs text-muted-foreground">
                  Markdown: paragraphs, lists and links. Images are not shown.
                </p>
                <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
                  Markdown
                </span>
              </div>
            </div>
          </form>

          <Link
            href="/profile/settings"
            className="card block px-6 py-4 flex items-center justify-between gap-4 hover:border-accent/50"
          >
            <span>
              <span className="block text-sm font-medium text-foreground">Account settings</span>
              <span className="block text-[13px] text-muted-foreground mt-0.5">
                Email preferences and privacy. {user.email}
              </span>
            </span>
            <ArrowRightIcon className="w-4 h-4 text-muted-foreground shrink-0" />
          </Link>
        </div>
      </section>

      <Dialog
        isOpen={framing !== null}
        onClose={() => setFraming(null)}
        labelledBy={CROP_TITLE_ID}
        className="max-w-xl"
      >
        {framing && (
          <>
            <h2 id={CROP_TITLE_ID} className="text-base font-semibold text-foreground">
              Frame your photo
            </h2>
            <p className="text-sm text-muted-foreground mt-1 mb-4">
              Drag to move, scroll or use the slider to zoom. The square is what
              everyone sees.
            </p>
            <ImageCropper
              src={framing.source.dataUrl}
              naturalWidth={framing.source.width}
              naturalHeight={framing.source.height}
              value={framing.crop}
              onChange={(crop) => setFraming({ source: framing.source, crop })}
              lockRatio={1}
              minSourceWidth={400}
              previewLabel="Avatar"
            />
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setFraming(null)}
                className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleCropConfirmed}
                className="px-4 py-2 text-sm font-medium rounded-lg bg-accent text-white hover:bg-accent/90"
              >
                Use it
              </button>
            </div>
          </>
        )}
      </Dialog>
    </main>
  );
}
