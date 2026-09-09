# Firasah — Project Context

Read this in full before starting work each session. Update it when a real decision gets made — treat it as living documentation, not a one-time brief.

## What this is

Firasah is a SaaS analytics platform for UK charities. It aggregates fundraising and social data — JustGiving, LaunchGood, Instagram, TikTok, Mailchimp/Klaviyo — into actionable dashboards, with three subscription tiers.

Primary purpose: **portfolio evidence for a job search**, not commercial traction. The person building this is pivoting from Financial Crime Data Analyst (PwC) into Analytics Engineer / Senior Data Analyst roles, targeting applications in Feb–Apr 2027. This project exists to demonstrate real, hands-on infrastructure skill — pipeline design, data modeling, architecture decisions — to technical interviewers and hiring managers who may read the code or ask about design choices directly.

Practical implication: prioritize code and architecture that's **defensible and explainable in an interview** over code that's merely fast to ship. Where there's a tradeoff between "quickest way to get this working" and "way that demonstrates understanding of why," lean toward the latter — but don't gold-plate parts of the stack that aren't the point (see "Not doing yet" below).

## Tech stack

- **Backend:** Python, FastAPI
- **Data:** dbt, Prefect (orchestration), BigQuery
- **Auth:** Supabase
- **Frontend:** Next.js, Recharts
- **Billing:** Stripe
- **Infra:** Docker, GCP Cloud Run

## Environment & setup notes

Operational specifics worth knowing before running anything — these are easy to rediscover the hard way if this section goes stale:

- **Python:** 3.12, managed via `uv`. Dependencies pinned in `pyproject.toml` + `uv.lock`. Core deps so far: `fastapi`, `dbt-core`, `dbt-bigquery`.
- **dbt is uv-managed, not on PATH directly.** Invoke it as:
  `uv run dbt <command> --project-dir dbt --profiles-dir ~/.dbt`
  from the repo root — plain `dbt <command>` won't work.
- **dbt project lives at `dbt/`** (a subfolder, not repo root).
- **BigQuery connection:** profile name `firasah`, target project `firasah-dev`, dataset `firasah_dev`, region `europe-west2`. Connection verified via `dbt debug`.
- **Credentials:** GCP service account key sits in `credentials/` (gitignored as a whole folder, not by filename).
- **Supabase project:** org `Firasah`, project `firasah-dev`, region London (eu-west-2). `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` set in `.env` (placeholders in `.env.example`). `supabase` added as a project dependency (via `uv add supabase`). Connection verified with the anon key via the Python client — no tables exist yet, so auth/schema wiring is still open (Phase 4).
- **FastAPI app:** entry point is `main.py` at repo root, currently just a `GET /health` route returning `{"status": "ok"}`. Run locally with `uv run uvicorn main:app --reload --port 8000`; interactive docs at `http://localhost:8000/docs`. `uvicorn` added as a dependency (via `uv add "uvicorn[standard]"`). Health check doesn't verify any dependency (Supabase/BigQuery) yet — placeholder only.
- **JustGiving API:** free developer account registered at `developer.justgiving.com`, AppID obtained. Test/dev environment is `api.staging.justgiving.com` — **not** `.sandbox.` (older blog posts and an archived SDK reference a `.sandbox` subdomain and `apimanagement.justgiving.com` that no longer resolve; the portal now runs on 3scale). AppID is sent as an `x-api-key` header (works for endpoints that don't require basic-auth user credentials). Staging charity id `2050` is JustGiving's built-in demo fixture ("The Demo Charity") — useful for auth checks without needing a real charity's data. `JUSTGIVING_APP_ID` set in `.env` (placeholder in `.env.example`). `httpx` and `python-dotenv` added as dependencies (via `uv add httpx python-dotenv`) — first use of `.env` loading in Python code so far. Verified with a one-off script at `scripts/check_justgiving_auth.py` (not part of the real ingestion pipeline).
- **JustGiving donations endpoint:** use `/v2/fundraising/pages/{pageShortName}/donations`, not the `/v1/...` version — V1 exists and returns 200s but its `pageNumber` query param silently doesn't advance results (confirmed empirically against staging), V2 fixes this. Query params are `pageNumber` and `pageSize`; response includes `pagination.totalPages` to know when to stop looping. `example-fundraising-page` is a real staging test page with 2 donations on it — useful for testing without needing your own fundraising page. `GetFundraisingPageDonations`'s sibling endpoint under `Charity/GetCharityDonations` looked relevant but only returns the top 4 "promoted" donations with no pagination — not useful for ingestion. The real ingestion script lives at `ingestion/justgiving_donations.py`; raw fetched output goes to `data/raw/` (gitignored — regenerated, not source) and to BigQuery table `firasah-dev.firasah_dev.raw_justgiving_donations` via a batch `load_table_from_json` job (schema autodetected, `WRITE_APPEND` — every pull adds rows rather than overwriting, tagged with `_page_short_name` and `_ingested_at`). `google-cloud-bigquery` added as an explicit dependency (was already present transitively via `dbt-bigquery`, but our own script imports it directly). Auth reuses the same `GOOGLE_APPLICATION_CREDENTIALS` service-account key dbt already uses, via Application Default Credentials — no separate BigQuery auth setup needed.
- **Prefect:** `fetch_donations` and `load_to_bigquery` are `@task`s, orchestrated by a `@flow` (`justgiving_donations_flow`) in the same file. Runs locally with no separate server needed — Prefect spins up a temporary local one automatically (`prefect run` shows "Starting temporary server..."). `PREFECT_SERVER_ANALYTICS_ENABLED=false` set in `.env` — without it, Prefect's own anonymous telemetry heartbeat throws a noisy (harmless) `database is locked` traceback on that temporary server's local SQLite file; doesn't affect the actual flow, just clutters output. **Gotcha hit once:** appending a new line to `.env` with `echo "X" >> .env` corrupted `JUSTGIVING_APP_ID` because the file didn't end in a trailing newline — the new var landed on the same line as the last one. Always confirm a trailing newline (or just edit the file directly) rather than blind-appending.
- **Ingestion connectors are a package now — run with `-m`, not by file path.** Phase 3 pulled the generic bits out of `ingestion/justgiving_donations.py` (retry/backoff, the BigQuery landing step) into `ingestion/common.py`, so every future connector (LaunchGood, Instagram, TikTok, Mailchimp/Klaviyo) reuses `get_with_retries`, `save_raw_json`, and `load_raw_to_bigquery` instead of reimplementing them. This means `justgiving_donations.py` now does `from ingestion.common import ...`, which only resolves if `ingestion/` is imported as a package — run it as `uv run python -m ingestion.justgiving_donations <page_short_name>` from the repo root, **not** `uv run python ingestion/justgiving_donations.py` (that fails with `ModuleNotFoundError: No module named 'ingestion'` because running a file directly puts its own directory on `sys.path`, not the repo root). Same rule will apply to every new connector added under `ingestion/`.
- **BigQuery free tier blocks DML (`dbt snapshot` limitation):** the `firasah-dev` GCP project doesn't have billing enabled, and BigQuery's free tier flatly rejects DML queries (`MERGE`/`UPDATE`/`DELETE`) — error: "Billing has not been enabled for this project... DML queries are not allowed in the free tier." This matters specifically for `dbt snapshot`: its *first* run per snapshot is a plain `CREATE TABLE` (works fine), but *every run after that* uses a `MERGE` to update the table — which fails until billing is enabled. Confirmed by trying to re-run `justgiving_donations_snapshot` to test refund detection. Not an issue for normal `dbt run`/`dbt test` (no DML there) or the Python ingestion script's `WRITE_APPEND` load job (also not DML) — only snapshots hit this. Enable billing when ready to actually exercise the snapshot's hard-delete detection live.

## Conventions

- **Commits:** Conventional commits (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`). Every session ends in a real commit — even an unfinished feature gets committed with a clear message, not left dangling locally.
- **Naming:** kebab-case for files, branches, and the repo itself.
- **Gitignore:** Python + Node coverage — `.env`, `__pycache__`, `node_modules`, `.idea`, `.vscode`, `credentials/` — already in place; keep it current as new tooling gets added.
- **Scope discipline:** work top-down through the roadmap below. Don't pull work forward from a later phase unless explicitly asked — even if it seems related or easy.

## Learning & explanation preferences

The person building this wants to genuinely understand the infrastructure they're shipping — this project is proof of skill, not just proof of output — but has a limited weekly learning budget and doesn't want to burn it memorizing boilerplate or syntax that carries no transferable understanding.

**When generating non-trivial code, flag what's actually worth understanding versus what's just implementation detail.**

**Worth flagging (call these out explicitly, briefly):**
- Architectural decisions and *why* one approach was chosen over an alternative (e.g. why a staging/intermediate/mart layering in dbt, why Prefect handles retries a certain way, why an endpoint is structured a particular way)
- Design patterns that will recur elsewhere or come up in interviews (auth flow logic, pipeline orchestration structure, data modeling choices, API design decisions)
- Anything that trades off cost, performance, or maintainability in a way a technical interviewer might probe
- Non-obvious gotchas specific to this stack (BigQuery quirks, dbt materialization choices, Supabase auth edge cases)

**Not worth flagging (skip silently):**
- Standard library usage, common syntax, boilerplate CRUD
- Repetitive config/scaffolding following a pattern already established once
- Verbose type hints or framework conventions that are just "how FastAPI/Next.js expects things structured"
- Anything where understanding it wouldn't transfer to a different tool or a job interview

**How to surface it:** end a meaningful chunk of work with a short "Worth understanding" callout — 2–4 bullet points max, plain language, no lecture. Not inline comments cluttering the code. If nothing in a chunk clears the bar, skip the callout entirely.

**Keep the language genuinely simple, not just short.** Most of this stack (dbt, BigQuery, uv, general backend/data infra) is being learned for the first time — write each bullet like explaining it to a smart friend with no background in that specific tool, not a peer engineer. Don't stack multiple unexplained technical terms in one sentence. If a technical term is needed, explain what it means in the same breath instead of assuming familiarity. A plain sentence that's slightly less precise beats a dense one that's exactly right but hard to follow.

## dbt learning status

Course (dbt Fundamentals, free): modules 1-2 done (Welcome, Analytics Development Lifecycle); 3, 4, 6 pending (Set Up dbt, Models, Data Tests). Building ahead of course completion deliberately — Claude Code teaches core dbt concepts directly during build sessions rather than assuming course knowledge; course modules get done afterward to consolidate/fill gaps, not as a gate before building.

**Concepts actually covered so far (via building, not the course):**
- Seeds vs sources — seeds are loaded by dbt itself via `dbt seed` and referenced with `ref()`; sources are raw data landed by something outside dbt and referenced with `source()`
- What a model is — a `.sql` file with a `SELECT`, compiled by dbt into a view or table
- Materializations — view vs table
- Why staging models exist — rename/cast only, no business logic, one file per source table
- Generic tests (`not_null`, `unique`) declared in schema `.yml` files
- Sources, for real this time — `source()` points at a table landed by something outside dbt (our own Python ingestion script, not `dbt seed`), declared in a `sources.yml` with `database`/`schema` keys (for BigQuery: `database` = GCP project, `schema` = dataset — non-obvious mapping since "database" isn't BigQuery's usual term for that)
- A real SQL gotcha, not dbt-specific but hit while building a staging model: naming a CTE the same as a column in it (`with source as (...)` + a column literally called `source`) makes a bare `select source` return the *entire row as a struct*, not the column — SQL resolves an unqualified name to a matching table/CTE alias before a column. Fix: don't name the CTE the same as any column you're pulling from it (renamed the convention from `source` to `raw` for this reason)

- Snapshots — solve "did this row's state change, or did it disappear entirely" over time. Config that mattered: `strategy='check'` + `check_cols` (tracks whether specific columns changed), and `invalidate_hard_deletes=True`, which is what actually detects a row vanishing from the source (e.g. a refunded donation no longer returned by the API) and marks it `dbt_valid_to` instead of us having to diff snapshots by hand. A snapshot's source query must return exactly one row per `unique_key` on every run — ours dedupes the append-only raw layer down to the latest-known version per `donation_id` first (`qualify row_number() ... = 1`)
- Snapshots behave differently on their first run vs. every run after: the first run is a plain `CREATE TABLE`; every run after that uses a `MERGE` to update existing rows and close out ones that vanished. That distinction matters a lot on BigQuery's free tier specifically — see the BigQuery snapshot/DML note under Environment & setup notes
- Intermediate/mart layers — `fct_` prefix is the dbt community convention for a fact table (one row per business event — here, one row per currently-active donation). Marts are materialized as `table`, not `view` like staging, since they're what a dashboard/BI tool queries repeatedly and shouldn't have to recompute the snapshot logic on every hit

**Not yet covered:** incremental models, packages, macros.

Update this section whenever the course progresses or a new concept gets covered in a build session — keep the "covered" list growing rather than replacing it wholesale, so it stays a genuine record of what can be assumed as known.

---

## Roadmap & Progress

The full build, phase by phase. Check items off as they're genuinely completed — not when started, not when "basically done." If a step was practiced or approximated rather than fully built (e.g. against fake seed data instead of a real API), leave it unchecked and add a short note.

### Phase 1 · Foundations & Scaffolding (~15-20 hrs)
Stand up the skeleton — repo, environments, whole stack running locally before a single feature exists.

- [x] Create the Git repo, branching setup and a real README
- [x] Set up the Python environment (uv) and project structure
- [x] Spin up a Supabase project (auth + Postgres)
- [x] Create the GCP project and a BigQuery dataset
- [x] Scaffold a hello-world FastAPI service
- [x] Wire up .env / secrets management
- [x] Confirm the whole stack runs locally, end to end

### Phase 2 · First Vertical Slice (~25-30 hrs)
Take JustGiving alone from API → raw storage → dbt → one clean table. Prove the pattern before scaling it.

- [x] Get JustGiving API access and auth working
- [x] Write the ingestion script — pagination, rate limits, error handling
- [x] Land raw JustGiving data in BigQuery
- [x] Wrap it in a basic Prefect flow
- [x] Define the dbt source and first staging model
- [x] Build one clean mart table you'd actually chart

**Refund/cancellation detection — resolved:** the JustGiving donations API doesn't expose a status field (confirmed by inspecting real response fields — no `Cancelled`/`Refunded` flag present), so the fix is `dbt/snapshots/justgiving_donations_snapshot.sql` with `invalidate_hard_deletes=True` — if a donation stops appearing in the source, dbt marks it invalid automatically rather than us diffing timestamps by hand. `dbt/models/marts/justgiving/fct_justgiving_donations.sql` selects only currently-valid rows from the snapshot (`dbt_valid_to is null`) — this is the actual "clean mart table to chart." **Caveat:** the hard-delete detection is architecturally correct and the baseline snapshot run succeeded, but re-running `dbt snapshot` to prove it live is currently blocked — see the BigQuery DML/billing note below. Verify this once billing is enabled.

**Real source + staging model built:** `dbt/models/staging/justgiving/_justgiving__sources.yml` declares the `justgiving` source pointing at `raw_justgiving_donations` (the table the Python ingestion script lands data into — see above). `stg_justgiving_donations` renames/casts the real API fields (including parsing JustGiving's `.NET`-style `donationDate` string into a real timestamp) and is intentionally *not* deduplicated — `donation_id` is `not_null`-tested but not `unique`-tested, since the append-only raw layer can legitimately contain the same donation more than once across pulls; dedup is deferred to the mart layer. `dbt run` and `dbt test` (6 tests, all `not_null`) pass. This replaced the earlier seed-based practice rep (deleted `dbt/seeds/justgiving_donations.csv` and its model) now that the real pattern works end to end.

**Milestone reached:** first real source flowing end to end — JustGiving API → raw BigQuery table → dbt staging model → snapshot → mart table, orchestrated by a Prefect flow.

### Phase 3 · Multi-Source Data Layer (~50-60 hrs)
Add LaunchGood, Instagram, TikTok and Mailchimp/Klaviyo. Generalise ingestion and build the full dbt model layer with tests and docs.

**Before starting "Schedule multi-source refreshes in Prefect" below:** enable billing on the `firasah-dev` GCP project (see the BigQuery free tier/DML note under Environment & setup notes). A recurring pipeline that includes `dbt snapshot` will hit BigQuery's free-tier DML block on every single scheduled run otherwise — this needs sorting before scheduling goes live, not after. Set a GCP budget alert at the same time (e.g. "email me if spend hits $1") — enabling billing doesn't mean you start paying (still get 1 TiB queries + 10 GB storage free per month), but the alert catches any genuine mistake early.

- [x] Generalise ingestion into a reusable connector shape
- [ ] Build the LaunchGood connector — **deferred, deliberately out of order.** LaunchGood has no public developer API (confirmed: no docs, no dev portal, nothing in their support center or GitHub org). Decided 2026-09-03 to skip it and build Instagram/TikTok/Mailchimp first (real official APIs), rather than block on either reverse-engineering LaunchGood's undocumented internal endpoint or waiting on a cold outreach email for partner access. Revisit once one of those two paths is chosen.
- [ ] Build the Instagram and TikTok connectors — **split, decided 2026-09-03.** Instagram (Graph API) is buildable now: "Standard Access" covers accounts you own with no Meta App Review needed, only Advanced Access (for other charities' accounts later) requires the 2-4 week review + verified business identity. Instagram setup stalled on getting a Facebook Page linked to a usable account (dormant personal FB accounts get throttled by Meta's anti-abuse checks on Page creation) — on hold, picked back up via a Page admin's own account instead of fighting the throttle. TikTok has no Instagram-style shortcut — any real access needs an app submitted for review (5-10 business days, sandbox demo required) regardless of whose account it is, so that's the one actively being progressed:
  - TikTok app created (type: Other, Individual), Sandbox mode enabled, Login Kit product added with scopes `user.info.basic`, `user.info.stats`, `video.list`, app icon uploaded, Terms/Privacy Policy site deployed on Netlify.
  - **Local dev callback + tunnel wired up (2026-09-09):** `main.py` has a placeholder route `GET /auth/tiktok/callback` (accepts `code`/`state` query params, just echoes them back — no real token exchange yet, that comes once past Sandbox). Exposed to the internet via ngrok on a free **static domain** `your-ngrok-static-domain.ngrok-free.dev`, reserved permanently to this ngrok account so the Redirect URI never changes across restarts. Redirect URI registered with TikTok: `https://your-ngrok-static-domain.ngrok-free.dev/auth/tiktok/callback`.
  - **To run locally:** `uv run uvicorn main:app --port 8000` in one terminal, `ngrok http --url=your-ngrok-static-domain.ngrok-free.dev 8000` in another (note: ngrok deprecated the `--domain` flag in favour of `--url` sometime in 2026 — `--domain` still works but prints a deprecation warning).
  - **Gotcha:** ngrok's free plan changed since its original "free static domains" announcement — as of 2026, typing your own custom subdomain name requires a paid Pay-as-you-go plan; the free tier only gives one **auto-assigned** random static domain (still permanent, still free, just not custom-named). `your-ngrok-static-domain` is that auto-assigned name, not a chosen one.
  - **Plan revised 2026-09-09 — review may not be needed at all for now.** Sandbox mode supports up to 10 whitelisted "target user" accounts and allows real OAuth + real API calls against them with no app review required — the test business TikTok account has been added as a target user. The restrictions Sandbox does have (forced-private posting, no Data Portability API) are about *publishing* content, not the read-only scopes this project needs (`user.info.basic`, `user.info.stats`, `video.list`). So: build and run the real connector against the target account under Sandbox first. Only submit for the 5-10 day review later if Firasah needs more than 10 test accounts or onboards real charities beyond dev/testing.
  - **TikTok connector built and verified end-to-end (2026-09-09).** Sandbox Client key + Client secret are in `.env` (`TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`). One-off `scripts/tiktok_oauth_exchange.py <code>` trades a fresh browser-authorized `code` for an access + refresh token (also added to `.env`, not part of the real pipeline — same "one-off auth-check script" pattern as JustGiving's `scripts/check_justgiving_auth.py`). The real connector is `ingestion/tiktok_videos.py`: refreshes the access token unconditionally at the start of every run (simpler than waiting for a 401, cheap enough for a manually-run flow), fetches videos via `video.list` (POST + cursor pagination) and account stats via `user.info` (GET), and lands both in BigQuery as `raw_tiktok_videos` and `raw_tiktok_user_info` via the shared `load_raw_to_bigquery` helper. First real run pulled 4 videos and live account stats (70 followers, 1,317 total likes) from the test business target account.
  - **Two `ingestion/common.py` additions made generalising for TikTok, both reused from JustGiving's shape:** `get_with_retries` was renamed to `request_with_retries` and generalised to any HTTP method (`client.request(method, url, **kwargs)`) since TikTok's `video.list` needs POST, unlike JustGiving's GET-only endpoint — JustGiving's call site was updated to match, regression-tested afterward, no behaviour change. Added `update_env_file(updates, path=".env")`, which rewrites specific `KEY=VALUE` lines in place (never blind-appends, always ends with a clean trailing newline) — needed because TikTok's refresh token *rotates* on every use and the old one stops working once it does, so the new one has to be persisted immediately or the next run breaks. Verified after the first real run: exactly one of each `TIKTOK_ACCESS_TOKEN`/`TIKTOK_REFRESH_TOKEN` line, no duplication, file length unchanged.
  - **Remaining for TikTok:** nothing blocking — Instagram is the still-open half of this checklist item (see above, on hold on Facebook Page setup).
- [ ] Build the Mailchimp/Klaviyo connector
- [ ] Model the staging layer for every source
- [ ] Build intermediate + mart models that unify the sources
- [ ] Add dbt tests (not_null, unique, relationships) and docs
- [ ] Schedule multi-source refreshes in Prefect

### Phase 4 · Backend API (~25-35 hrs)
Build the FastAPI layer that serves modelled data to the frontend — endpoints, auth, and strict per-charity data isolation.

- [ ] Design the endpoints the dashboard actually needs
- [ ] Wire Supabase auth into the backend
- [ ] Build the query layer that serves marts from BigQuery
- [ ] Enforce per-charity data isolation (multi-tenancy)
- [ ] Add caching and sensible response shaping
- [ ] Write basic API tests

### Phase 5 · Dashboard Frontend (~50-65 hrs)
Build what charities actually see — Next.js/React dashboards with Tailwind and Recharts, wired to your backend.

- [ ] Scaffold the Next.js app and auth flow
- [ ] Build the app shell, nav and routing
- [ ] Build the core dashboard views
- [ ] Wire Recharts visualisations to live data
- [ ] Handle loading, empty and error states
- [ ] Polish and make it responsive down to mobile

**Milestone (not yet reached):** portfolio-ready — a working multi-source dashboard demoable even before billing or deploy. This is the point it earns its place in the job search.

### Phase 6 · Billing & Subscription Tiers (~25-30 hrs)
Add Stripe, three tiers, checkout and feature-gating.

- [ ] Define the three tiers and what each one unlocks
- [ ] Integrate Stripe Checkout and the customer portal
- [ ] Handle webhooks and subscription state
- [ ] Gate features by tier in both backend and frontend
- [ ] Test the upgrade / downgrade / cancel flows

### Phase 7 · Ship It — Deploy & Beta (~25-35 hrs)
Dockerise, deploy to Cloud Run, set up CI/CD, onboard the first real charity. This is the MVP.

- [ ] Dockerise the backend and frontend
- [ ] Deploy to Cloud Run with proper env/secrets
- [ ] Set up GitHub Actions CI/CD
- [ ] Add logging and basic monitoring
- [ ] Buy the domain and wire it up
- [ ] Onboard your first beta charity

**Milestone (not yet reached):** MVP shipped — Firasah is live, real data, real user. The core build is done.

### Phase 8 · Agentic AI Layer (post-MVP — open-ended)
Layer autonomous agents on top of Firasah — drafting and emailing weekly reports, chasing up Slack campaigns, acting on the data it already holds.

- [ ] Pick an agent framework (LangGraph or MS Agent Framework)
- [ ] Give an agent read-access to Firasah's marts as tools
- [ ] Build the weekly-report drafting agent
- [ ] Add email drafting and sending
- [ ] Build the Slack campaign chase-up agent
- [ ] Add guardrails and human-in-the-loop review

## Not doing yet / explicitly deferred

- Stripe integration — not until MVP phase
- Agentic AI layer — final phase, not before the rest is solid
- Deep hands-on depth on tools outside the core stack (e.g. Databricks/Spark) — conceptual fluency mapped to BigQuery/dbt experience is sufficient; not worth build time given the job-search timeline

---

## How Claude Code should use this file

**When asked "where should I continue" / "what's next":** scan the roadmap top to bottom, phase by phase, and find the *first* unchecked `- [ ]` item. State which phase it's in and give a one-line reminder of what the step involves. Don't jump ahead to a later phase's steps even if they seem more relevant to something just discussed.

**When told a step is done:** update that specific checkbox to `- [x]`. If it's genuinely ambiguous whether something counts as fully done — ask, or check it off with a short caveat note rather than marking it cleanly complete.

**Proactively, at the end of any session where real progress happened** — don't wait to be asked: update the relevant roadmap checkboxes, add or extend notes on anything partially done, and update the "dbt learning status" section if a new concept was covered. Then stage and commit this file specifically (`docs: update roadmap progress`).

**Don't** restructure, reorder, delete steps, or add new phases without being explicitly asked — only toggle checkboxes and extend notes. The shape of the plan is intentional; only the progress markers change during normal sessions.