import { LogOut } from "lucide-react";

import { signOut } from "@/app/actions/auth";
import { attempt } from "@/components/card";
import { getMe } from "@/lib/api";

export async function OrgBadge() {
  // If the lookup fails the shell still renders (sign-out stays usable);
  // a login redirect from attempt() still goes through.
  const me = await attempt(getMe);
  return (
    <div className="sb-center flex items-center justify-between gap-2">
      <div className="sb-hide min-w-0">
        {me && (
          <>
            <p className="text-xs text-muted">Signed in to</p>
            <p className="line-clamp-2 text-sm font-medium">
              {me.org_name ?? me.org_id}
            </p>
          </>
        )}
      </div>
      <form action={signOut}>
        <button
          type="submit"
          title="Sign out"
          className="rounded-md p-2 text-muted hover:bg-surface-sunken hover:text-ink"
        >
          <LogOut size={16} aria-hidden />
          <span className="sr-only">Sign out</span>
        </button>
      </form>
    </div>
  );
}

export function OrgBadgeFallback() {
  return <div className="h-10 animate-pulse rounded-md bg-surface-sunken" />;
}
