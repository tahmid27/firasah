import { redirect } from "next/navigation";

import { signInToDemo } from "@/lib/demo";
import { createClient } from "@/lib/supabase/server";

// A shareable link straight into the demo (e.g. firasah.uk/demo on a CV).
// Someone already signed in keeps their own session and just goes to the app.
export async function GET() {
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  if (!data?.claims && !(await signInToDemo())) {
    redirect("/login");
  }
  redirect("/");
}
