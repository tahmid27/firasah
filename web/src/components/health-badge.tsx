import {
  AlertTriangle,
  CheckCircle2,
  CircleSlash,
  Upload,
  XCircle,
} from "lucide-react";

import { HEALTH_LABELS, type HealthState } from "@/lib/source-status";

const STYLES: Record<
  HealthState,
  { icon: typeof CheckCircle2; className: string }
> = {
  ok: { icon: CheckCircle2, className: "text-status-good" },
  stale: { icon: AlertTriangle, className: "text-status-warning" },
  failed: { icon: XCircle, className: "text-status-critical" },
  manual: { icon: Upload, className: "text-muted" },
  not_connected: { icon: CircleSlash, className: "text-muted" },
};

// Status colour always comes with an icon and words.
export function HealthBadge({ state }: { state: HealthState }) {
  const { icon: Icon, className } = STYLES[state];
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-ink-2">
      <Icon size={14} className={className} aria-hidden />
      {HEALTH_LABELS[state]}
    </span>
  );
}
