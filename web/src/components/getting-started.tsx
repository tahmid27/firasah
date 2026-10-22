import Link from "next/link";

import { attempt } from "@/components/card";
import { connectedSources } from "@/lib/api";

// Shown on Overview only while no source has sent anything yet, i.e. a brand
// new charity. Once any source has data it disappears.
export async function GettingStarted() {
  const connected = await attempt(connectedSources);
  if (!connected || connected.size > 0) return null;
  return (
    <section className="rounded-lg border border-border bg-accent-soft p-(--card-pad)">
      <h2 className="font-heading text-base font-semibold tracking-tight">
        Welcome to Firasah
      </h2>
      <p className="mt-1 max-w-prose text-sm text-ink-2">
        No data has arrived yet. Once your accounts are connected, your first
        numbers appear after the next daily refresh (around 6am UK time). The{" "}
        <Link href="/data-health" className="text-accent underline">
          Data health
        </Link>{" "}
        page shows the status of each connection.
      </p>
    </section>
  );
}
