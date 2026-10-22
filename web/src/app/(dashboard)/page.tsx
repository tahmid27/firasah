import { Suspense } from "react";

import { CardSkeleton } from "@/components/card";
import { GettingStarted } from "@/components/getting-started";
import { PageShell } from "@/components/page-shell";

import {
  AudienceTile,
  DataHealthCard,
  IncomeCard,
  LatestActivityCard,
  RaisedTile,
  TopFundraisersCard,
} from "./_overview/cards";

// Each card loads on its own behind Suspense, so the API calls run in
// parallel and a slow or failing one doesn't hold up the rest.
export default function Home() {
  return (
    <PageShell
      title="Overview"
      description="How fundraising, social and email are doing at a glance."
    >
      <Suspense fallback={null}>
        <GettingStarted />
      </Suspense>
      <div className="grid gap-(--card-gap) md:grid-cols-3">
        <Suspense fallback={<CardSkeleton title="Raised this month" />}>
          <RaisedTile />
        </Suspense>
        <Suspense fallback={<CardSkeleton title="Social followers" />}>
          <AudienceTile metric="followers" />
        </Suspense>
        <Suspense fallback={<CardSkeleton title="Email subscribers" />}>
          <AudienceTile metric="email_subscribers" />
        </Suspense>
      </div>
      <div className="grid gap-(--card-gap) lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Suspense
            fallback={
              <CardSkeleton title="Income, last 12 months" height="h-56" />
            }
          >
            <IncomeCard />
          </Suspense>
        </div>
        <Suspense fallback={<CardSkeleton title="Data health" height="h-56" />}>
          <DataHealthCard />
        </Suspense>
      </div>
      <div className="grid gap-(--card-gap) lg:grid-cols-2">
        <Suspense
          fallback={
            <CardSkeleton title="Top fundraisers this month" height="h-48" />
          }
        >
          <TopFundraisersCard />
        </Suspense>
        <Suspense
          fallback={
            <CardSkeleton title="Latest post and email" height="h-48" />
          }
        >
          <LatestActivityCard />
        </Suspense>
      </div>
    </PageShell>
  );
}
