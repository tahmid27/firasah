import { createClient } from "@/lib/supabase/server";

// Signs in as the public demo charity. The credentials live in server-only
// environment variables and never reach the browser.
export async function signInToDemo(): Promise<boolean> {
  const email = process.env.FIRASAH_DEMO_EMAIL;
  const password = process.env.FIRASAH_DEMO_PASSWORD;
  if (!email || !password) return false;

  const supabase = await createClient();
  const { error } = await supabase.auth.signInWithPassword({ email, password });
  return !error;
}
