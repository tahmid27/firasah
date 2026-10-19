"use client";

import { useActionState } from "react";

import { signIn, type LoginState } from "@/app/actions/auth";

const initialState: LoginState = { error: null, email: "" };

export function LoginForm() {
  const [state, formAction, pending] = useActionState(signIn, initialState);

  return (
    <form action={formAction} className="flex flex-col gap-4">
      <label className="flex flex-col gap-1 text-sm text-ink-2">
        Email
        <input
          name="email"
          type="email"
          autoComplete="email"
          defaultValue={state.email}
          required
          className="rounded-md border border-border bg-surface px-3 py-2 text-base text-ink focus:outline-2 focus:outline-accent"
        />
      </label>
      <label className="flex flex-col gap-1 text-sm text-ink-2">
        Password
        <input
          name="password"
          type="password"
          autoComplete="current-password"
          required
          className="rounded-md border border-border bg-surface px-3 py-2 text-base text-ink focus:outline-2 focus:outline-accent"
        />
      </label>
      {state.error && (
        <p role="alert" className="text-sm text-danger">
          {state.error}
        </p>
      )}
      <button
        type="submit"
        disabled={pending}
        className="mt-2 rounded-md bg-accent px-3 py-2 font-medium text-accent-ink hover:opacity-90 disabled:opacity-60"
      >
        {pending ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}
