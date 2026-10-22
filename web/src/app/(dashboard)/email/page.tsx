import type { Metadata } from "next";
import { Suspense } from "react";

import { CardSkeleton } from "@/components/card";
import { PageShell } from "@/components/page-shell";

import {
  CampaignsCard,
  EmailTotals,
  GrowthCard,
  LinksCard,
  ListHealthCard,
  SendTimesCard,
} from "./cards";

export const metadata: Metadata = { title: "Email · Firasah" };

export default function EmailPage({ searchParams }: PageProps<"/email">) {
  return (
    <PageShell
      title="Email"
      description="Mailchimp campaigns and the health of your list."
      searchParams={searchParams}
    >
      <Suspense
        fallback={
          <div className="grid gap-(--card-gap) sm:grid-cols-2 lg:grid-cols-4">
            <CardSkeleton title="Campaigns sent" height="h-12" />
            <CardSkeleton title="Open rate" height="h-12" />
            <CardSkeleton title="Click rate" height="h-12" />
            <CardSkeleton title="Unsubscribes" height="h-12" />
          </div>
        }
      >
        <EmailTotals searchParams={searchParams} />
      </Suspense>
      <Suspense fallback={<CardSkeleton title="Campaigns" height="h-64" />}>
        <CampaignsCard searchParams={searchParams} />
      </Suspense>
      <div id="links" className="grid scroll-mt-6 gap-(--card-gap) lg:grid-cols-2">
        <Suspense
          fallback={
            <CardSkeleton title="Which links were clicked" height="h-48" />
          }
        >
          <LinksCard searchParams={searchParams} />
        </Suspense>
        <Suspense
          fallback={
            <CardSkeleton title="When people open and click" height="h-52" />
          }
        >
          <SendTimesCard searchParams={searchParams} />
        </Suspense>
      </div>
      <div className="grid gap-(--card-gap) lg:grid-cols-2">
        <Suspense
          fallback={<CardSkeleton title="Audience growth" height="h-60" />}
        >
          <GrowthCard searchParams={searchParams} />
        </Suspense>
        <Suspense fallback={<CardSkeleton title="List health" height="h-60" />}>
          <ListHealthCard searchParams={searchParams} />
        </Suspense>
      </div>
    </PageShell>
  );
}
