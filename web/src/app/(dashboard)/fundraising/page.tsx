import type { Metadata } from "next";

import { PageShell } from "@/components/page-shell";
import { PlannedVisuals } from "@/components/planned-visuals";

export const metadata: Metadata = { title: "Fundraising · Firasah" };

export default function FundraisingPage({
  searchParams,
}: PageProps<"/fundraising">) {
  return (
    <PageShell
      title="Fundraising"
      description="Donations across JustGiving and LaunchGood."
      searchParams={searchParams}
    >
      <PlannedVisuals
        items={[
          ["F1", "Income over time, by platform"],
          ["F2", "Fundraiser leaderboard"],
          ["F3", "Projects"],
          ["F4", "Gift sizes"],
          ["F5", "Gift Aid"],
          ["F6", "Zakat"],
          ["F7", "Fees: gross vs net"],
          ["F8", "Traffic sources"],
          ["F9", "Progress vs target"],
          ["F10", "When people give (day × hour)"],
        ]}
      />
    </PageShell>
  );
}
