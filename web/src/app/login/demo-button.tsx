"use client";

import { useActionState } from "react";

import { signInAsDemo, type DemoState } from "@/app/actions/auth";

const initialState: DemoState = { error: null };

export function DemoButton() {
  const [state, formAction, pending] = useActionState(
    signInAsDemo,
    initialState,
  );

  return (
    <form action={formAction} className="flex flex-col gap-2">
      <button
        type="submit"
        disabled={pending}
        className="rounded-md border border-border bg-surface px-3 py-2 font-medium text-ink hover:bg-surface-sunken disabled:opacity-60"
      >
        {pending ? "Opening the demo…" : "Click here for demo"}
      </button>
      <p className="text-center text-xs text-ink-2">
        Explore Clearwater Relief, a fictional charity with made-up data. No
        sign-up needed.
      </p>
      {state.error && (
        <p role="alert" className="text-center text-sm text-danger">
          {state.error}
        </p>
      )}
    </form>
  );
}
