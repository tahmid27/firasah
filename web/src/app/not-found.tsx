import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex flex-1 items-center justify-center px-4 py-24">
      <div className="max-w-sm text-center">
        <h1 className="mb-2 font-heading text-xl font-bold tracking-tight">
          Page not found
        </h1>
        <p className="mb-6 text-sm text-ink-2">
          That page doesn&apos;t exist, or the link is out of date.
        </p>
        <Link href="/" className="text-sm text-accent underline">
          Back to Overview
        </Link>
      </div>
    </main>
  );
}
