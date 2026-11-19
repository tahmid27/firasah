"use server";

import { redirect } from "next/navigation";

import { createClient } from "@/lib/supabase/server";

export type LoginState = { error: string | null; email: string };

export async function signIn(
  _previous: LoginState,
  formData: FormData,
): Promise<LoginState> {
  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "");
  if (!email || !password) {
    return { error: "Enter your email and password.", email };
  }

  const supabase = await createClient();
  const { error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) {
    // Same message for a wrong email or a wrong password.
    return { error: "That email and password don't match.", email };
  }
  redirect("/");
}

export type DemoState = { error: string | null };

// Signs in as the public demo charity. The credentials live in server-only
// environment variables and never reach the browser.
export async function signInAsDemo(): Promise<DemoState> {
  const email = process.env.FIRASAH_DEMO_EMAIL;
  const password = process.env.FIRASAH_DEMO_PASSWORD;
  if (!email || !password) {
    return { error: "The demo isn't available right now." };
  }

  const supabase = await createClient();
  const { error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) {
    return { error: "The demo isn't available right now." };
  }
  redirect("/");
}

export async function signOut() {
  const supabase = await createClient();
  await supabase.auth.signOut();
  redirect("/login");
}
