"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useTransition } from "react";

import { platformName } from "@/lib/platforms";

// All / one platform, kept in the URL (?platform=) like the date range.
export function PlatformFilter({ platforms }: { platforms: string[] }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [pending, startTransition] = useTransition();
  const selected = searchParams.get("platform") ?? "";

  const choose = (value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set("platform", value);
    else next.delete("platform");
    const query = next.toString();
    startTransition(() =>
      router.push(`${pathname}${query ? `?${query}` : ""}`, { scroll: false }),
    );
  };

  return (
    <div
      role="radiogroup"
      aria-label="Platform"
      className={`flex rounded-md border border-border bg-surface-sunken p-0.5 text-sm ${
        pending ? "opacity-60" : ""
      }`}
    >
      {["", ...platforms].map((value) => (
        <button
          key={value || "all"}
          type="button"
          role="radio"
          aria-checked={selected === value}
          onClick={() => choose(value)}
          className={`rounded px-3 py-1.5 ${
            selected === value
              ? "bg-surface text-ink shadow-xs"
              : "text-muted hover:text-ink"
          }`}
        >
          {value ? platformName(value) : "All"}
        </button>
      ))}
    </div>
  );
}
