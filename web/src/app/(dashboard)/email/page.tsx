import type { Metadata } from "next";

import { PageShell } from "@/components/page-shell";
import { PlannedVisuals } from "@/components/planned-visuals";

export const metadata: Metadata = { title: "Email · Firasah" };

export default function EmailPage({ searchParams }: PageProps<"/email">) {
  return (
    <PageShell
      title="Email"
      description="Mailchimp campaigns and the health of your list."
      searchParams={searchParams}
    >
      <PlannedVisuals
        items={[
          ["E1", "Campaign table"],
          ["E2", "Link clicks per campaign"],
          ["E3", "Audience growth"],
          ["E4", "List health"],
          ["E5", "Send-time pattern"],
        ]}
      />
    </PageShell>
  );
}
