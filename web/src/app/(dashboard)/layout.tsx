import { Suspense } from "react";

import { Brand } from "@/components/brand";
import { MobileNav } from "@/components/mobile-nav";
import { NavLinks } from "@/components/nav-links";
import { OrgBadge, OrgBadgeFallback } from "@/components/org-badge";
import { SidebarToggle } from "@/components/sidebar-toggle";
import { ThemeToggle } from "@/components/theme-toggle";

// Not an auth check: the proxy redirects logged-out visitors, and every data
// call is checked by the API. The charity name streams in behind Suspense so
// the rest of the shell isn't held up by it.
export default function DashboardLayout({ children }: LayoutProps<"/">) {
  const footer = (
    <div className="flex flex-col gap-3">
      <ThemeToggle />
      <Suspense fallback={<OrgBadgeFallback />}>
        <OrgBadge />
      </Suspense>
    </div>
  );

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <aside className="sb-aside sticky top-0 hidden h-screen w-60 shrink-0 flex-col gap-8 border-r border-hairline bg-surface px-3 py-5 md:flex">
        <div className="sb-center sb-pad flex px-3">
          <Brand />
        </div>
        <nav aria-label="Main">
          <NavLinks />
        </nav>
        <div className="sb-pad mt-auto flex flex-col gap-3 border-t border-hairline px-3 pt-4">
          <SidebarToggle />
          {footer}
        </div>
      </aside>
      <MobileNav footer={footer} />
      <main className="min-w-0 flex-1 px-4 py-6 md:px-8 md:py-8">
        {children}
      </main>
    </div>
  );
}
