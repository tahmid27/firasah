import type { Metadata } from "next";
import { Suspense } from "react";

import { CardSkeleton } from "@/components/card";
import { PageShell } from "@/components/page-shell";

import { EmailLiftCard, TimelineCard, WindowCard } from "./cards";

export const metadata: Metadata = { title: "Appeals · Firasah" };

export default function AppealsPage({ searchParams }: PageProps<"/appeals">) {
  return (
    <PageShell
      title="Appeals"
      description="How posts and emails line up with giving. Pick the dates of an appeal to see it against the period before."
      searchParams={searchParams}
    >
      <Suspense
        fallback={
          <CardSkeleton
            title="This period against the one before"
            height="h-40"
          />
        }
      >
        <WindowCard searchParams={searchParams} />
      </Suspense>
      <Suspense
        fallback={
          <CardSkeleton title="Donations, posts and emails" height="h-72" />
        }
      >
        <TimelineCard searchParams={searchParams} />
      </Suspense>
      <Suspense
        fallback={
          <CardSkeleton title="Giving around each email" height="h-48" />
        }
      >
        <EmailLiftCard searchParams={searchParams} />
      </Suspense>
    </PageShell>
  );
}
