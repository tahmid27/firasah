"use client";

import { AlertCircle } from "lucide-react";

// Catches a page that fails as a whole (individual cards handle their own
// failures). The error text is never shown: it can contain internal details.
export function ErrorView({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-3 py-24 text-center">
      <AlertCircle size={28} className="text-status-critical" aria-hidden />
      <h1 className="font-heading text-xl font-bold tracking-tight">
        Something went wrong
      </h1>
      <p className="text-sm text-ink-2">
        This page couldn&apos;t load. Try again, and if it keeps happening, tell
        us.
      </p>
      {error.digest && (
        <p className="text-xs text-muted">Reference: {error.digest}</p>
      )}
      <button
        type="button"
        onClick={reset}
        className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-ink"
      >
        Try again
      </button>
    </div>
  );
}
