import { connection } from "next/server";
import { Suspense, type ReactNode } from "react";

import { londonToday, resolveRange } from "@/lib/date-range";

import { DateRangePicker } from "./date-range-picker";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

type Props = {
  title: string;
  description: string;
  searchParams?: SearchParams;
  children: ReactNode;
};

// Title and description are static and prerender; the date-range control
// reads the URL, so it streams in behind its own boundary.
export function PageShell({
  title,
  description,
  searchParams,
  children,
}: Props) {
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          <p className="mt-1 text-sm text-ink-2">{description}</p>
        </div>
        {searchParams && (
          <Suspense
            fallback={<div className="h-9 w-56 rounded-md bg-surface-sunken" />}
          >
            <RangeControl searchParams={searchParams} />
          </Suspense>
        )}
      </header>
      {children}
    </div>
  );
}

async function RangeControl({ searchParams }: { searchParams: SearchParams }) {
  await connection(); // "today" must be worked out per request, not at build
  const params = await searchParams;
  const today = londonToday();
  const range = resolveRange(params, today);
  return (
    <DateRangePicker
      key={`${range.start}|${range.end}`}
      range={range}
      today={today}
    />
  );
}
