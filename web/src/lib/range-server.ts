import "server-only";

import { connection } from "next/server";

import { londonToday, resolveRange, type DateRange } from "./date-range";

export type SearchParams = Promise<
  Record<string, string | string[] | undefined>
>;

// The page's date range from its URL. "Today" is read per request, never at
// build time.
export async function rangeFrom(
  searchParams: SearchParams,
): Promise<DateRange & { today: string }> {
  await connection();
  const params = await searchParams;
  const today = londonToday();
  return { ...resolveRange(params, today), today };
}

export function param(
  params: Record<string, string | string[] | undefined>,
  key: string,
): string | undefined {
  const value = params[key];
  return Array.isArray(value) ? value[0] : value;
}

// Weekly bars for short ranges, monthly for longer ones.
export function intervalFor(range: DateRange): "week" | "month" {
  const days =
    (Date.parse(range.end) - Date.parse(range.start)) / 86_400_000 + 1;
  return days <= 92 ? "week" : "month";
}

// The same number of days immediately before the range.
export function previousRange(range: DateRange) {
  const day = 86_400_000;
  const length = Date.parse(range.end) - Date.parse(range.start);
  const end = new Date(Date.parse(range.start) - day);
  const start = new Date(end.getTime() - length);
  return {
    start: start.toISOString().slice(0, 10),
    end: end.toISOString().slice(0, 10),
  };
}
