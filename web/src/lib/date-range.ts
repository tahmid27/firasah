// The date range lives in the URL (?range=90d, or ?range=custom&from=&to=), so
// every page in a tab shares it, links can be shared, and Back works. Dates
// are plain YYYY-MM-DD strings in UK time, the same as the API takes.

export const PRESETS = [
  { key: "30d", label: "Last 30 days" },
  { key: "90d", label: "Last 90 days" },
  { key: "12m", label: "Last 12 months" },
  { key: "ytd", label: "Year to date" },
  { key: "3y", label: "Last 3 years" },
] as const;

export type PresetKey = (typeof PRESETS)[number]["key"];
export const DEFAULT_PRESET: PresetKey = "12m";
export const RANGE_PARAMS = ["range", "from", "to"] as const;

export type DateRange = {
  preset: PresetKey | "custom";
  start: string;
  end: string;
  label: string;
};

type Params = Record<string, string | string[] | undefined>;

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

export function londonToday(now: Date = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/London",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(now);
}

function parse(date: string): Date {
  return new Date(`${date}T00:00:00Z`);
}

function format(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function addDays(date: string, days: number): string {
  const d = parse(date);
  d.setUTCDate(d.getUTCDate() + days);
  return format(d);
}

function addMonths(date: string, months: number): string {
  const d = parse(date);
  d.setUTCMonth(d.getUTCMonth() + months);
  return format(d);
}

function isValidDate(value: string | undefined): value is string {
  return !!value && ISO_DATE.test(value) && format(parse(value)) === value;
}

function presetStart(preset: PresetKey, today: string): string {
  switch (preset) {
    case "30d":
      return addDays(today, -29);
    case "90d":
      return addDays(today, -89);
    case "12m":
      return addDays(addMonths(today, -12), 1);
    case "ytd":
      return `${today.slice(0, 4)}-01-01`;
    case "3y":
      return addDays(addMonths(today, -36), 1);
  }
}

export function formatDay(date: string, withYear = true): string {
  return parse(date).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    ...(withYear ? { year: "numeric" } : {}),
    timeZone: "UTC",
  });
}

export function rangeLabel(start: string, end: string): string {
  const sameYear = start.slice(0, 4) === end.slice(0, 4);
  return `${formatDay(start, !sameYear)} – ${formatDay(end)}`;
}

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

// Anything unreadable falls back to the default rather than erroring.
export function resolveRange(params: Params, today: string): DateRange {
  const preset = first(params.range);
  const from = first(params.from);
  const to = first(params.to);

  if (preset === "custom" && isValidDate(from) && isValidDate(to)) {
    const end = to > today ? today : to;
    if (from <= end) {
      return {
        preset: "custom",
        start: from,
        end,
        label: rangeLabel(from, end),
      };
    }
  }

  const key = PRESETS.some((p) => p.key === preset)
    ? (preset as PresetKey)
    : DEFAULT_PRESET;
  const start = presetStart(key, today);
  return { preset: key, start, end: today, label: rangeLabel(start, today) };
}

// Query string for a range, keeping any other params already in the URL.
export function withRange(
  current: URLSearchParams,
  range: { preset: string; from?: string; to?: string },
): string {
  const next = new URLSearchParams(current);
  RANGE_PARAMS.forEach((key) => next.delete(key));
  if (range.preset !== DEFAULT_PRESET) next.set("range", range.preset);
  if (range.preset === "custom" && range.from && range.to) {
    next.set("from", range.from);
    next.set("to", range.to);
  }
  const query = next.toString();
  return query ? `?${query}` : "";
}

// Only the range params, for carrying the range across tabs.
export function rangeOnly(current: URLSearchParams): string {
  const next = new URLSearchParams();
  RANGE_PARAMS.forEach((key) => {
    const value = current.get(key);
    if (value) next.set(key, value);
  });
  const query = next.toString();
  return query ? `?${query}` : "";
}
