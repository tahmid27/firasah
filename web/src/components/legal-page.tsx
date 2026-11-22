import Link from "next/link";

import { Brand } from "@/components/brand";

export function LegalPage({
  title,
  updated,
  children,
}: {
  title: string;
  updated: string;
  children: React.ReactNode;
}) {
  return (
    <main className="mx-auto w-full max-w-2xl flex-1 px-4 py-12">
      <Link href="/login" aria-label="Back to sign in">
        <Brand />
      </Link>
      <h1 className="mt-8 font-heading text-2xl font-bold tracking-tight">
        {title}
      </h1>
      <p className="mb-8 mt-1 text-sm text-ink-2">Last updated {updated}</p>
      <div className="space-y-4 text-sm leading-6 [&_h2]:mt-8 [&_h2]:font-heading [&_h2]:text-base [&_h2]:font-bold [&_ul]:list-disc [&_ul]:space-y-1 [&_ul]:pl-5">
        {children}
      </div>
      <p className="mt-10 text-xs text-ink-2">
        <Link href="/privacy" className="underline">
          Privacy policy
        </Link>
        {" · "}
        <Link href="/terms" className="underline">
          Terms of use
        </Link>
      </p>
    </main>
  );
}
