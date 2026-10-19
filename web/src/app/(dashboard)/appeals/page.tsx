import type { Metadata } from "next";

import { PageShell } from "@/components/page-shell";
import { PlannedVisuals } from "@/components/planned-visuals";

export const metadata: Metadata = { title: "Appeals · Firasah" };

export default function AppealsPage({ searchParams }: PageProps<"/appeals">) {
  return (
    <PageShell
      title="Appeals"
      description="How posts and emails line up with giving."
      searchParams={searchParams}
    >
      <PlannedVisuals
        items={[
          ["A1", "Timeline: daily donations with post and email markers"],
          ["A2", "Window report vs the period before"],
          ["A3", "Email lift"],
        ]}
      />
    </PageShell>
  );
}
