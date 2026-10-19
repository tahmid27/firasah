import { Suspense, type ReactNode } from "react";

import { rangeFrom, type SearchParams } from "@/lib/range-server";

import { DateRangePicker } from "./date-range-picker";

type Props = {
  title: string;
  description: string;
  searchParams?: SearchParams;
  // Extra filters shown before the date range (e.g. platform on Social)
  controls?: ReactNode;
  children: ReactNode;
};

// Title and description are static and prerender; the date-range control
// reads the URL, so it streams in behind its own boundary.
export function PageShell({
  title,
  description,
  searchParams,
  controls,
  children,
}: Props) {
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          <p className="mt-1 text-sm text-ink-2">{description}</p>
        </div>
        {(controls || searchParams) && (
          <div className="flex flex-wrap items-center gap-2">
            {controls}
            {searchParams && (
              <Suspense
                fallback={
                  <div className="h-9 w-56 rounded-md bg-surface-sunken" />
                }
              >
                <RangeControl searchParams={searchParams} />
              </Suspense>
            )}
          </div>
        )}
      </header>
      {children}
    </div>
  );
}

async function RangeControl({ searchParams }: { searchParams: SearchParams }) {
  const { today, ...range } = await rangeFrom(searchParams);
  return (
    <DateRangePicker
      key={`${range.start}|${range.end}`}
      range={range}
      today={today}
    />
  );
}
