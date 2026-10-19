import { Suspense } from "react";

import { signOut } from "@/app/actions/auth";
import { getMe } from "@/lib/api";

// Placeholder home page until the app shell is built (Phase 5, step 2).
export default function Home() {
  return (
    <main className="flex flex-1 items-center justify-center px-4">
      <Suspense fallback={<p className="text-neutral-500">Loading…</p>}>
        <Welcome />
      </Suspense>
    </main>
  );
}

async function Welcome() {
  const me = await getMe();
  return (
    <div className="text-center">
      <p className="text-sm text-neutral-500">Signed in to</p>
      <h1 className="mb-6 text-2xl font-semibold">
        {me.org_name ?? me.org_id}
      </h1>
      <form action={signOut}>
        <button className="underline">Sign out</button>
      </form>
    </div>
  );
}
