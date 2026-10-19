import { signOut } from "@/app/actions/auth";

export default function NoCharityPage() {
  return (
    <main className="flex flex-1 items-center justify-center px-4">
      <div className="max-w-sm text-center">
        <h1 className="mb-2 text-xl font-semibold">No charity linked</h1>
        <p className="mb-6 text-neutral-600">
          Your account isn&apos;t linked to a charity yet. Ask your
          charity&apos;s Firasah admin to add you.
        </p>
        <form action={signOut}>
          <button className="underline">Sign out</button>
        </form>
      </div>
    </main>
  );
}
