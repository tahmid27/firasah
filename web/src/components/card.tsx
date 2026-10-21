import { AlertCircle } from "lucide-react";
import { unstable_rethrow } from "next/navigation";
import type { ReactNode } from "react";

type CardProps = {
  title: string;
  subtitle?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
};

export function Card({
  title,
  subtitle,
  action,
  children,
  className = "",
}: CardProps) {
  return (
    <section
      className={`flex min-w-0 flex-col gap-(--card-gap) rounded-lg border border-border bg-surface p-(--card-pad) ${className}`}
    >
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-heading text-base font-semibold tracking-tight text-ink">{title}</h2>
          {subtitle && <p className="mt-0.5 text-xs text-muted">{subtitle}</p>}
        </div>
        {action}
      </header>
      {children}
    </section>
  );
}

export function CardSkeleton({
  title,
  height = "h-24",
}: {
  title: string;
  height?: string;
}) {
  return (
    <Card title={title}>
      <div
        aria-hidden
        className={`${height} animate-pulse rounded-md bg-surface-sunken`}
      />
      <span className="sr-only">Loading</span>
    </Card>
  );
}

export function CardError({ title }: { title: string }) {
  return (
    <Card title={title}>
      <p className="flex items-center gap-2 text-sm text-ink-2">
        <AlertCircle size={16} className="text-status-critical" aria-hidden />
        Couldn&apos;t load this right now. Try refreshing.
      </p>
    </Card>
  );
}

// Lets one card fail without taking the page down. Next's own control-flow
// errors (redirect to /login, etc.) are rethrown, not swallowed.
export async function attempt<T>(
  load: () => Promise<T>,
): Promise<T | undefined> {
  try {
    return await load();
  } catch (error) {
    unstable_rethrow(error);
    console.error(error);
    return undefined;
  }
}
