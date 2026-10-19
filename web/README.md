# Firasah dashboard

Next.js app for the Firasah API. See the root README for how to run it.

- `src/proxy.ts`: refreshes the Supabase session cookie and redirects by login state (a convenience; the API is the security boundary).
- `src/lib/api.ts`: the only place that calls the API. Runs on the server, forwards the user's Supabase token, and sends 401 to `/login` and 403 to `/no-charity`.
- `src/lib/api-types.ts`: generated from the API's OpenAPI spec (`npm run gen:api`); CI fails if it's out of date.
