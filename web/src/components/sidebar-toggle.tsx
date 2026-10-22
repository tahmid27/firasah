"use client";

import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { useSyncExternalStore } from "react";

import { applySidebar, readSidebar } from "@/lib/sidebar";

const listeners = new Set<() => void>();
function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function SidebarToggle() {
  // The server can't know the saved choice, so it renders "expanded" and the
  // real choice appears after hydration.
  const state = useSyncExternalStore(subscribe, readSidebar, () => "expanded");
  const collapsed = state === "collapsed";
  const Icon = collapsed ? PanelLeftOpen : PanelLeftClose;
  const label = collapsed ? "Expand sidebar" : "Collapse sidebar";

  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      onClick={() => {
        applySidebar(collapsed ? "expanded" : "collapsed");
        listeners.forEach((l) => l());
      }}
      className="sb-center flex items-center gap-3 rounded-md px-3 py-2 text-sm text-ink-2 hover:bg-surface-sunken hover:text-ink"
    >
      <Icon size={18} strokeWidth={1.75} className="shrink-0 text-muted" aria-hidden />
      <span className="sb-hide">Collapse sidebar</span>
    </button>
  );
}
