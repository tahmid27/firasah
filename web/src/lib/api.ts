import "server-only";

import createFetchClient from "openapi-fetch";
import { redirect } from "next/navigation";
import { connection } from "next/server";
import { cache } from "react";

import type { paths } from "./api-types";
import { createClient } from "./supabase/server";

export class ApiError extends Error {
  constructor(public status: number) {
    super(`API request failed with status ${status}`);
  }
}

// API calls are made from the Next.js server, never the browser, so the API
// needs no CORS. The token is forwarded as-is: the API verifies it and looks
// up the charity, so nothing here is trusted for access decisions.
export async function apiClient() {
  await connection(); // per-request: never prerender a charity's data
  const supabase = await createClient();
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (!token) redirect("/login");

  const client = createFetchClient<paths>({
    baseUrl: process.env.FIRASAH_API_URL,
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  client.use({
    onResponse({ response }) {
      if (response.status === 401) redirect("/login");
      if (response.status === 403) redirect("/no-charity");
      if (!response.ok) throw new ApiError(response.status);
      return response;
    },
  });
  return client;
}

// Non-2xx responses throw in the middleware above, so data is always set.
export function unwrap<T>(result: { data?: T }): T {
  if (result.data === undefined) throw new ApiError(500);
  return result.data;
}

export const getMe = cache(async () => {
  const api = await apiClient();
  return unwrap(await api.GET("/me"));
});

// Shared by more than one card on a page: one API call per request.
export const getFundraisingSummary = cache(async () => {
  const api = await apiClient();
  return unwrap(await api.GET("/fundraising/summary"));
});

export const getOverviewSummary = cache(async () => {
  const api = await apiClient();
  return unwrap(await api.GET("/overview/summary"));
});

// Which sources are connected, so cards can explain what doesn't apply.
export const getDataHealth = cache(async () => {
  const api = await apiClient();
  return unwrap(await api.GET("/data-health/sources"));
});

export async function connectedSources(): Promise<Set<string>> {
  const health = await getDataHealth();
  return new Set(
    health.sources
      .filter((s) => s.last_data_at || s.last_run_at)
      .map((s) => s.source),
  );
}
