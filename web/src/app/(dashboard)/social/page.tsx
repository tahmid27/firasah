import type { Metadata } from "next";

import { PageShell } from "@/components/page-shell";
import { PlannedVisuals } from "@/components/planned-visuals";

export const metadata: Metadata = { title: "Social · Firasah" };

export default function SocialPage({ searchParams }: PageProps<"/social">) {
  return (
    <PageShell
      title="Social"
      description="Instagram and TikTok: audience and what's working."
      searchParams={searchParams}
    >
      <PlannedVisuals
        items={[
          ["S1", "Followers over time"],
          ["S2", "Net followers gained or lost"],
          ["S3", "Posts table"],
          ["S4", "Format comparison"],
          ["S5", "Posting consistency"],
          ["S6", "Best time to post (day × hour)"],
          ["S7", "Instagram daily reach, views and accounts engaged"],
          ["S8", "Follower demographics"],
        ]}
      />
    </PageShell>
  );
}
