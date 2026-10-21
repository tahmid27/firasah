import type { Metadata } from "next";
import { Suspense } from "react";

import { CardSkeleton } from "@/components/card";
import { PageShell } from "@/components/page-shell";

import {
  FeesCard,
  GiftAidCard,
  GiftSizesCard,
  IncomeCard,
  LeaderboardCard,
  ProjectsCard,
  TargetsCard,
  TimingCard,
  TotalsTiles,
  TrafficCard,
  ZakatCard,
} from "./cards";

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
      <Suspense
        fallback={
          <div className="grid gap-(--card-gap) sm:grid-cols-3">
            <CardSkeleton title="Raised" height="h-12" />
            <CardSkeleton title="Donations" height="h-12" />
            <CardSkeleton title="Average donation" height="h-12" />
          </div>
        }
      >
        <TotalsTiles searchParams={searchParams} />
      </Suspense>
      <Suspense
        fallback={<CardSkeleton title="Income over time" height="h-64" />}
      >
        <IncomeCard searchParams={searchParams} />
      </Suspense>
      <div className="grid gap-(--card-gap) lg:grid-cols-2">
        <Suspense fallback={<CardSkeleton title="Projects" height="h-48" />}>
          <ProjectsCard searchParams={searchParams} />
        </Suspense>
        <Suspense
          fallback={
            <CardSkeleton title="Progress against targets" height="h-48" />
          }
        >
          <TargetsCard searchParams={searchParams} />
        </Suspense>
      </div>
      <div id="leaderboard" className="scroll-mt-6">
        <Suspense
          fallback={
            <CardSkeleton title="Fundraiser leaderboard" height="h-64" />
          }
        >
          <LeaderboardCard searchParams={searchParams} />
        </Suspense>
      </div>
      <div className="grid gap-(--card-gap) lg:grid-cols-2">
        <Suspense
          fallback={
            <CardSkeleton title="Where donations came from" height="h-56" />
          }
        >
          <TrafficCard searchParams={searchParams} />
        </Suspense>
        <Suspense
          fallback={<CardSkeleton title="Donation sizes" height="h-56" />}
        >
          <GiftSizesCard searchParams={searchParams} />
        </Suspense>
      </div>
      <Suspense
        fallback={<CardSkeleton title="When people give" height="h-56" />}
      >
        <TimingCard searchParams={searchParams} />
      </Suspense>
      <div className="grid gap-(--card-gap) md:grid-cols-3">
        <Suspense fallback={<CardSkeleton title="Gift Aid" />}>
          <GiftAidCard searchParams={searchParams} />
        </Suspense>
        <Suspense fallback={<CardSkeleton title="Zakat" />}>
          <ZakatCard searchParams={searchParams} />
        </Suspense>
        <Suspense fallback={<CardSkeleton title="Platform fees" />}>
          <FeesCard searchParams={searchParams} />
        </Suspense>
      </div>
    </PageShell>
  );
}
