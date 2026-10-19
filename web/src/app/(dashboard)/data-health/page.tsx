import type { Metadata } from "next";

import { PageShell } from "@/components/page-shell";
import { PlannedVisuals } from "@/components/planned-visuals";

export const metadata: Metadata = { title: "Data health · Firasah" };

export default function DataHealthPage() {
  return (
    <PageShell
      title="Data health"
      description="When each source last updated, and anything that failed."
    >
      <PlannedVisuals items={[["D1", "Source table"]]} />
    </PageShell>
  );
}
