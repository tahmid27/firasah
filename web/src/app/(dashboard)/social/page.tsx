import type { Metadata } from "next";
import { Suspense } from "react";

import { CardSkeleton } from "@/components/card";
import { PageShell } from "@/components/page-shell";

import {
  BestTimeCard,
  ConsistencyCard,
  DemographicsCard,
  FollowersCard,
  FormatsCard,
  InstagramActivityCard,
  NetFollowersCard,
  PostsCard,
  SocialPlatformControl,
  SocialTotals,
} from "./cards";

export const metadata: Metadata = { title: "Social · Firasah" };

export default function SocialPage({ searchParams }: PageProps<"/social">) {
  return (
    <PageShell
      title="Social"
      description="Instagram and TikTok: audience and what's working."
      searchParams={searchParams}
      controls={
        <Suspense>
          <SocialPlatformControl />
        </Suspense>
      }
    >
      <Suspense
        fallback={
          <div className="grid gap-4 sm:grid-cols-3">
            <CardSkeleton title="Followers" height="h-12" />
            <CardSkeleton title="Posts published" height="h-12" />
            <CardSkeleton title="Average engagement" height="h-12" />
          </div>
        }
      >
        <SocialTotals searchParams={searchParams} />
      </Suspense>
      <div className="grid gap-4 lg:grid-cols-2">
        <Suspense
          fallback={<CardSkeleton title="Followers over time" height="h-60" />}
        >
          <FollowersCard searchParams={searchParams} />
        </Suspense>
        <Suspense
          fallback={
            <CardSkeleton title="Followers gained or lost" height="h-60" />
          }
        >
          <NetFollowersCard searchParams={searchParams} />
        </Suspense>
      </div>
      <div id="posts" className="scroll-mt-6">
        <Suspense fallback={<CardSkeleton title="Posts" height="h-64" />}>
          <PostsCard searchParams={searchParams} />
        </Suspense>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Suspense
          fallback={
            <CardSkeleton title="What format works best" height="h-48" />
          }
        >
          <FormatsCard searchParams={searchParams} />
        </Suspense>
        <Suspense
          fallback={<CardSkeleton title="Posting consistency" height="h-48" />}
        >
          <ConsistencyCard searchParams={searchParams} />
        </Suspense>
      </div>
      <Suspense
        fallback={<CardSkeleton title="Best time to post" height="h-56" />}
      >
        <BestTimeCard searchParams={searchParams} />
      </Suspense>
      <Suspense
        fallback={
          <CardSkeleton title="Instagram account activity" height="h-60" />
        }
      >
        <InstagramActivityCard searchParams={searchParams} />
      </Suspense>
      <Suspense
        fallback={
          <CardSkeleton
            title="Who your Instagram followers are"
            height="h-40"
          />
        }
      >
        <DemographicsCard />
      </Suspense>
    </PageShell>
  );
}
