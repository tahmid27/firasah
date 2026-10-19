import type { components } from "./api-types";

type SourceStatus = components["schemas"]["SourceStatus"];

export type HealthState =
  | "ok"
  | "stale"
  | "failed"
  | "manual"
  | "not_connected";

// The refresh runs daily at 06:00, so anything older than a day and a bit
// means at least one run was missed.
const STALE_AFTER_HOURS = 30;

// LaunchGood has no API: someone uploads an export by hand, so "old" there
// is normal and not a fault.
const MANUAL_SOURCES = new Set(["launchgood"]);

export function healthOf(source: SourceStatus): HealthState {
  if (!source.last_data_at && !source.last_run_at) return "not_connected";
  if (source.last_run_status === "failed") return "failed";
  if (MANUAL_SOURCES.has(source.source)) return "manual";
  if (
    source.hours_since_data === null ||
    source.hours_since_data > STALE_AFTER_HOURS
  ) {
    return "stale";
  }
  return "ok";
}

export const HEALTH_LABELS: Record<HealthState, string> = {
  ok: "Up to date",
  stale: "Out of date",
  failed: "Last refresh failed",
  manual: "Manual upload",
  not_connected: "Not connected",
};
