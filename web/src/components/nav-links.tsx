"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { rangeOnly } from "@/lib/date-range";
import { NAV_ITEMS, isActive } from "@/lib/nav";

type Props = { onNavigate?: () => void };

// Links carry the current date range to every tab, including ones that
// don't use it, so it survives passing through them. Reading the URL's query
// needs a Suspense boundary, so the fallback is the same list without it.
export function NavLinks(props: Props) {
  return (
    <Suspense fallback={<NavList query="" {...props} />}>
      <NavLinksWithRange {...props} />
    </Suspense>
  );
}

function NavLinksWithRange(props: Props) {
  const searchParams = useSearchParams();
  return <NavList query={rangeOnly(searchParams)} {...props} />;
}

function NavList({ query, onNavigate }: Props & { query: string }) {
  const pathname = usePathname();
  return (
    <ul className="flex flex-col gap-0.5">
      {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
        const active = isActive(pathname, href);
        return (
          <li key={href}>
            <Link
              href={`${href}${query}`}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              title={label}
              className={`sb-center flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                active
                  ? "bg-accent-soft font-medium text-ink"
                  : "text-ink-2 hover:bg-surface-sunken hover:text-ink"
              }`}
            >
              <Icon
                size={18}
                strokeWidth={1.75}
                className={`shrink-0 ${active ? "text-accent" : "text-muted"}`}
                aria-hidden
              />
              <span className="sb-hide">{label}</span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
