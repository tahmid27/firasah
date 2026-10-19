import { PageShell } from "@/components/page-shell";
import { PlannedVisuals } from "@/components/planned-visuals";

export default function Home() {
  return (
    <PageShell
      title="Overview"
      description="How fundraising, social and email are doing at a glance."
    >
      <PlannedVisuals
        items={[
          [
            "O1",
            "Headline tiles: raised this month vs last, % change, donations, average gift",
          ],
          ["O2", "Followers (Instagram + TikTok), now vs 30 days ago"],
          ["O3", "Email subscribers, now vs 30 days ago"],
          ["O4", "Income over the last 12 months (mini line)"],
          ["O5", "Data health strip"],
          ["O6", "Top 5 fundraisers this month"],
          ["O7", "Latest post and latest email"],
        ]}
      />
    </PageShell>
  );
}
