const gbpWhole = new Intl.NumberFormat("en-GB", {
  style: "currency",
  currency: "GBP",
  maximumFractionDigits: 0,
});
const gbpPence = new Intl.NumberFormat("en-GB", {
  style: "currency",
  currency: "GBP",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const gbpCompact = new Intl.NumberFormat("en-GB", {
  style: "currency",
  currency: "GBP",
  notation: "compact",
  maximumFractionDigits: 1,
});
const whole = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 });

export const gbp = (value: number) => gbpWhole.format(value);
export const gbpExact = (value: number) => gbpPence.format(value);
export const gbpShort = (value: number) => gbpCompact.format(value);
export const count = (value: number) => whole.format(value);

// Rates from the API are fractions (0.241 = 24.1%); changes are already percent.
export const rate = (fraction: number, digits = 1) =>
  `${(fraction * 100).toFixed(digits)}%`;
export const percent = (value: number, digits = 1) =>
  `${Math.abs(value).toFixed(digits)}%`;

export function signed(value: number) {
  return `${value > 0 ? "+" : value < 0 ? "−" : ""}${whole.format(Math.abs(value))}`;
}

const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

// API dates are YYYY-MM-DD (or ISO timestamps); read the date part directly so
// no timezone shift can move it a day.
export function monthShort(isoDate: string) {
  return MONTHS[Number(isoDate.slice(5, 7)) - 1];
}

export function monthYear(isoDate: string) {
  return `${monthShort(isoDate)} ${isoDate.slice(0, 4)}`;
}

export function dayMonth(isoDate: string) {
  return `${Number(isoDate.slice(8, 10))} ${monthShort(isoDate)}`;
}

// A timestamp's date in UK time, as "8 Oct 2026".
export function ukDate(timestamp: string) {
  const isoDate = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/London",
  }).format(new Date(timestamp));
  return `${dayMonth(isoDate)} ${isoDate.slice(0, 4)}`;
}

export function ago(hours: number) {
  if (hours < 1) return "under an hour ago";
  if (hours < 48)
    return `${Math.round(hours)} hour${Math.round(hours) === 1 ? "" : "s"} ago`;
  const days = Math.round(hours / 24);
  return `${days} days ago`;
}
