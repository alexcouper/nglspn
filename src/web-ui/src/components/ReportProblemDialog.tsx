"use client";

import { useState, type ComponentType, type SVGProps } from "react";
import {
  ChatBubbleLeftEllipsisIcon,
  CheckCircleIcon,
  LinkSlashIcon,
  SignalSlashIcon,
  WrenchScrewdriverIcon,
} from "@heroicons/react/24/outline";

import { Dialog } from "@/components/Dialog";
import { useAuth } from "@/contexts/auth";
import { api } from "@/lib/api";
import { ApiRequestError } from "@/lib/api/base";
import type { ProjectReportReason } from "@/lib/api";

const DETAILS_MAX = 2000;

interface Reason {
  id: ProjectReportReason;
  title: string;
  hint: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  placeholder: string;
}

// The titles match ProjectReportReason's labels on the backend, which is what
// the makers read in the email — so the visitor picks the words they'll see.
const REASONS: Reason[] = [
  {
    id: "site_down",
    title: "The site won't load",
    hint: "A blank page, an error, or it times out",
    icon: SignalSlashIcon,
    placeholder: "e.g. It shows a 502 error on the front page",
  },
  {
    id: "something_broken",
    title: "Something on the site is broken",
    hint: "A button, form or page doesn't work",
    icon: WrenchScrewdriverIcon,
    placeholder: "e.g. Signing up fails after I enter my email",
  },
  {
    id: "wrong_link",
    title: "The link goes somewhere else",
    hint: "A parked domain, another site, or a 404",
    icon: LinkSlashIcon,
    placeholder: "e.g. The domain now shows a 'for sale' page",
  },
  {
    id: "other",
    title: "Something else",
    hint: "Tell the makers in your own words",
    icon: ChatBubbleLeftEllipsisIcon,
    placeholder: "What should the makers know?",
  },
];

interface ReportProblemDialogProps {
  isOpen: boolean;
  onClose: () => void;
  projectSlugOrId: string;
  projectTitle: string;
  // False for an unclaimed tip-off. Its reports go to the Naglasúpan team, and
  // a visitor leaving an address has to be told that before they send it.
  hasMakers: boolean;
}

export function ReportProblemDialog(props: ReportProblemDialogProps) {
  // Mounted only while open, so every report starts from a blank form rather
  // than the last one's leftovers.
  if (!props.isOpen) return null;
  return <ReportProblemForm {...props} />;
}

function ReportProblemForm({
  onClose,
  projectSlugOrId,
  projectTitle,
  hasMakers,
}: ReportProblemDialogProps) {
  const { user } = useAuth();
  const [reason, setReason] = useState<ProjectReportReason | null>(null);
  const [details, setDetails] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  // A signed-in visitor's address is on file, but it is only handed to the
  // makers when they tick this. Nothing is shared by default.
  const [shareMyEmail, setShareMyEmail] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isSent, setIsSent] = useState(false);
  const [error, setError] = useState("");

  const selected = REASONS.find((r) => r.id === reason);
  const name = projectTitle || "this project";
  const recipients = hasMakers ? "the makers" : "the Naglasúpan team";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason) return;
    setIsSending(true);
    setError("");
    try {
      await api.projects.report(projectSlugOrId, {
        reason,
        details: details.trim(),
        contact_email: user
          ? shareMyEmail
            ? user.email
            : ""
          : contactEmail.trim(),
      });
      setIsSent(true);
    } catch (err) {
      if (err instanceof ApiRequestError && err.status === 429) {
        setError(
          "You've sent a few reports in a short time. Please try again later.",
        );
      } else if (err instanceof ApiRequestError && err.status === 422) {
        setError("Please check the email address and try again.");
      } else {
        setError("Couldn't send the report. Please try again.");
      }
    } finally {
      setIsSending(false);
    }
  };

  if (isSent) {
    return (
      <Dialog isOpen onClose={onClose} labelledBy="report-problem-title">
        <div className="text-center py-2">
          <CheckCircleIcon className="w-12 h-12 text-emerald-500 mx-auto" />
          <h2
            id="report-problem-title"
            className="text-lg font-semibold text-foreground mt-3"
          >
            Thanks for letting them know
          </h2>
          <p className="text-sm text-muted-foreground mt-2">
            Your report on{" "}
            <span className="text-foreground font-medium">{name}</span> is with
            us, and we&apos;ll make sure {recipients} hear about it.
          </p>
          <button
            type="button"
            onClick={onClose}
            className="btn-primary mt-6 w-full"
          >
            Done
          </button>
        </div>
      </Dialog>
    );
  }

  return (
    <Dialog
      isOpen
      onClose={onClose}
      labelledBy="report-problem-title"
      // Four reasons, a textarea and an email field outgrow a short window.
      // Dialog doesn't scroll (it is overflow-visible for popovers), so the
      // panel has to, or the send button ends up below the fold.
      className="max-w-lg max-h-[calc(100dvh-2rem)] overflow-y-auto max-sm:max-h-full"
      fullScreenOnMobile
    >
      <form onSubmit={handleSubmit} className="flex flex-col max-sm:h-full">
        <h2
          id="report-problem-title"
          className="text-lg font-semibold text-foreground"
        >
          Something not working?
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          {hasMakers ? (
            <>
              Let the makers of{" "}
              <span className="text-foreground font-medium">{name}</span> know.
              We pass your report on to them by email.
            </>
          ) : (
            <>
              <span className="text-foreground font-medium">{name}</span>{" "}
              has no maker on Naglasúpan, so your report goes to the
              Naglasúpan team.
            </>
          )}
        </p>

        <fieldset className="mt-5">
          <legend className="text-sm font-medium text-foreground mb-2">
            What&apos;s wrong?
          </legend>
          <div className="grid gap-2">
            {REASONS.map((r) => {
              const Icon = r.icon;
              const isSelected = reason === r.id;
              return (
                <label
                  key={r.id}
                  className={`flex items-center gap-3 rounded-lg border px-3 py-2.5 cursor-pointer transition-colors has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-accent/40 ${
                    isSelected
                      ? "border-accent bg-accent-subtle"
                      : "border-border hover:bg-muted"
                  }`}
                >
                  <input
                    type="radio"
                    name="report-reason"
                    value={r.id}
                    checked={isSelected}
                    onChange={() => setReason(r.id)}
                    className="sr-only"
                  />
                  <span
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-md ${
                      isSelected
                        ? "bg-accent text-white"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    <Icon className="w-5 h-5" aria-hidden="true" />
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm font-medium text-foreground">
                      {r.title}
                    </span>
                    <span className="block text-xs text-muted-foreground">
                      {r.hint}
                    </span>
                  </span>
                </label>
              );
            })}
          </div>
        </fieldset>

        <div className="mt-5">
          <div className="flex items-baseline justify-between mb-1.5">
            <label
              htmlFor="report-details"
              className="text-sm font-medium text-foreground"
            >
              What happened?{" "}
              <span className="font-normal text-muted-foreground">
                (optional)
              </span>
            </label>
            <span className="text-xs text-muted-foreground tabular-nums">
              {details.length}/{DETAILS_MAX}
            </span>
          </div>
          <textarea
            id="report-details"
            value={details}
            onChange={(e) => setDetails(e.target.value)}
            maxLength={DETAILS_MAX}
            rows={3}
            placeholder={selected?.placeholder ?? "What did you see?"}
            className="input"
          />
        </div>

        <div className="mt-4">
          {user ? (
            <label className="flex items-start gap-2 text-sm text-foreground cursor-pointer">
              <input
                type="checkbox"
                checked={shareMyEmail}
                onChange={(e) => setShareMyEmail(e.target.checked)}
                className="mt-0.5"
              />
              <span>
                Let {recipients} reply to me at{" "}
                <span className="font-medium">{user.email}</span>
              </span>
            </label>
          ) : (
            <>
              <label
                htmlFor="report-contact"
                className="block text-sm font-medium text-foreground mb-1.5"
              >
                Your email{" "}
                <span className="font-normal text-muted-foreground">
                  (optional)
                </span>
              </label>
              <input
                id="report-contact"
                type="email"
                value={contactEmail}
                onChange={(e) => setContactEmail(e.target.value)}
                maxLength={254}
                autoComplete="email"
                placeholder="you@example.com"
                className="input"
              />
              <p className="text-xs text-muted-foreground mt-1.5">
                Only shared with {recipients}, so they can ask you about it.
              </p>
            </>
          )}
        </div>

        {error && (
          <p role="alert" className="text-red-600 text-sm mt-4">
            {error}
          </p>
        )}

        <div className="flex gap-2 justify-end mt-6 max-sm:mt-auto max-sm:pt-6">
          <button
            type="button"
            onClick={onClose}
            disabled={isSending}
            className="btn-secondary"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSending || reason === null}
            className="btn-primary"
          >
            {isSending ? "Sending..." : "Send report"}
          </button>
        </div>
      </form>
    </Dialog>
  );
}
