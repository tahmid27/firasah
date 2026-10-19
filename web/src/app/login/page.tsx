import type { Metadata } from "next";

import { Brand } from "@/components/brand";

import { LoginForm } from "./login-form";

export const metadata: Metadata = { title: "Sign in · Firasah" };

export default function LoginPage() {
  return (
    <main className="flex flex-1 items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm rounded-xl border border-border bg-surface p-6 shadow-sm sm:p-8">
        <Brand />
        <h1 className="mt-6 text-xl font-semibold">Sign in</h1>
        <p className="mb-6 mt-1 text-sm text-ink-2">
          Your charity&apos;s fundraising, social and email in one place.
        </p>
        <LoginForm />
      </div>
    </main>
  );
}
