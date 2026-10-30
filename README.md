# Firasah

[![CI](https://github.com/tahmid27/firasah/actions/workflows/ci.yml/badge.svg)](https://github.com/tahmid27/firasah/actions/workflows/ci.yml)

An analytics platform for UK charities. Charities raise money and build audiences across a scatter of platforms that don't talk to each other. A fundraising manager who wants to know "did that Instagram push actually move donations?" currently exports several CSVs and fights a spreadsheet.

Firasah pulls those sources into one warehouse on a schedule, models them into tables that mean the same thing across platforms, and serves a per-charity dashboard on top, with each charity able to see only its own data.

| Area | Sources |
| --- | --- |
| Fundraising | JustGiving (API), LaunchGood (manual CSV export, since it has no public API) |
| Social | Instagram (Graph API), TikTok (Content API) |
| Email | Mailchimp (API) |

Built solo, end to end: connectors, warehouse modelling, a secured API, and the dashboard. The emphasis is on the data platform: connector design, modelling, testing, tenant isolation, and decisions that can be defended.

## At a glance

- **5 source connectors** on one shared ingestion framework, orchestrated by Prefect
- **33 dbt models** (staging → snapshot → intermediate → marts) and **134 dbt tests**, including a custom multi-tenant uniqueness test
- **FastAPI** service with **28 endpoints**, Supabase JWT auth and strict per-charity data isolation
- **Next.js + Recharts** dashboard: 6 pages, about 34 visuals, light and dark themes, usable down to phone width
- **266 pytest tests** plus a live isolation check that creates a second tenant and tries to read the first
- A **synthetic data generator** for three fake charities (about 108,000 donations over three years) that runs through the real connectors' parsing code and every dbt model

## Architecture

```
  JustGiving API ─┐
      TikTok API ─┤   ingestion/*.py        raw_* tables             dbt
   Mailchimp API ─┼─► (shared common.py) ─►  BigQuery    ─►  staging (views)
  LaunchGood CSV ─┤    Prefect flows         append-only             │
   Instagram API ─┘                       tagged with org_id         ▼
                                                                 snapshot
                                                          (change + deletions)
                                                                     │
                                                                     ▼
                                                    intermediate (cross-source unions)
                                                                     │
                                                                     ▼
                                                        marts (fct_ / dim_ tables)
                                                                     │
                                          Supabase JWT ─►  FastAPI (org_id injected on every query)
                                                                     │
                                                                     ▼
                                                  Next.js dashboard (server-side API calls)
```

Four ideas hold it together:

1. **Raw is append-only and untouched.** Nothing is renamed, cast, filtered or deduplicated on the way in. Every run appends a full pull tagged with when it arrived and which charity it belongs to. If the cleaning logic turns out wrong, fix the model and rebuild; never re-pull from the API.
2. **All cleaning is SQL, in dbt, in version control.**
3. **Each layer has one job.** Staging renames and casts. Snapshots track change over time. Intermediate models unify sources. Marts answer business questions.
4. **The charity is never taken from the request.** `org_id` comes only from the verified login token plus a server-side membership lookup, and one query builder adds `WHERE org_id = @org_id` to every query.

## Where to look

If you're reading the code, these are the most representative pieces:

| What | Where |
| --- | --- |
| Shared connector plumbing: retries, `Retry-After`, the BigQuery loader | [ingestion/common.py](ingestion/common.py) |
| A connector with cursor pagination and per-format API rules | [ingestion/instagram_posts.py](ingestion/instagram_posts.py) |
| The refresh flow: connectors → snapshot → run → test, with per-source failure isolation | [ingestion/refresh.py](ingestion/refresh.py) |
| Refund detection for an API with no refund flag | [dbt/snapshots/justgiving_donations_snapshot.sql](dbt/snapshots/justgiving_donations_snapshot.sql) |
| Cross-source union into one donations shape | [dbt/models/intermediate/fundraising/int_donations_unioned.sql](dbt/models/intermediate/fundraising/int_donations_unioned.sql) |
| Custom dbt test for multi-tenant keys | [dbt/tests/generic/unique_per_org.sql](dbt/tests/generic/unique_per_org.sql) |
| JWT verification (ES256 only, JWKS) | [api/auth.py](api/auth.py) |
| The allowlisted, parameterised query builder | [api/warehouse.py](api/warehouse.py) |
| Cross-tenant tests over every endpoint | [tests/test_api_endpoints.py](tests/test_api_endpoints.py) |
| Synthetic data generator | [synthetic/](synthetic/) |

## Data model

| Mart | Grain | Notes |
| --- | --- | --- |
| `fct_donations` | one row per active donation, JustGiving + LaunchGood | refund-aware on the JustGiving side; project → fundraiser → donation hierarchy |
| `dim_fundraising_pages` | one row per JustGiving page | targets, status, totals, Gift Aid estimate |
| `fct_social_posts` | one row per post, Instagram + TikTok | latest-known stats per post |
| `fct_social_account_stats` | one row per account per ingestion run | deliberately not deduplicated: the history is what makes a follower-growth chart possible |
| `fct_social_account_daily`, `fct_social_follower_demographics` | Instagram daily insights; follower breakdowns | latest pull per day / one set per run |
| `fct_mailchimp_campaigns` | one row per sent campaign | latest-known stats |
| `fct_mailchimp_audience_stats`, `_audience_daily`, `_audience_monthly` | audience size and growth | kept as history |
| `fct_mailchimp_link_clicks`, `fct_mailchimp_campaign_hourly` | clicks per link; opens by hour after send | |
| `fct_source_status` | one row per source | last data time and last refresh result; powers the Data health page |

Where only one platform offers a metric (TikTok views, LaunchGood Zakat amount), the unified table keeps the column and leaves the other platform's rows null rather than dropping the data.

## Multi-tenancy

Every raw row carries an `org_id`, and every staging model, snapshot key, dedup and join includes it. At the API:

- Supabase JWTs are verified against the project's published keys (ES256 only; required `exp`/`sub`/`aud`/`iss`; one generic 401 for every failure).
- The caller's charity is looked up on every request using the caller's own token, so Postgres row-level security applies and removing a member takes effect immediately.
- Endpoints can only reach BigQuery through a warehouse object built from a verified charity. A test fails if any other file touches BigQuery, or if any route is missing the auth dependency.
- Another charity's resource returns 404, identical to a missing one.

How it's tested: every endpoint is run as charity A and as charity B against a fake warehouse that answers only for the charity in the query's parameters; forged tokens (`alg: none`, key confusion, wrong issuer, expired) are rejected; and `scripts/check_tenancy_live` creates a temporary second charity against the real services, checks 80 things, and deletes it. The guards were each verified by deliberately breaking the code and watching the tests fail.

## Synthetic data

Real charities' data can't be put in a public repo, and the test accounts are tiny, so `synthetic/` generates three fake charities (small, medium, large) over three years: about 108,000 donations, 2,000 posts and 280 campaigns. It is generated as **raw-shaped** records in each platform's real format and fed through the connectors' own parsing code, the real loader and every dbt model, so it tests the pipeline instead of faking its output. A test checks every generated record has exactly the real APIs' field names.

The generator models Ramadan, Eid and the last ten nights, Giving Tuesday, paydays, repeat donors, Gift Aid, Zakat, refunds and a couple of foreign-currency gifts. Most emails and posts are drawn to have no measurable effect on giving, a few a modest one, and rare ones a large one, so the dashboard isn't scripted to tell a flattering story. Seeded, so it is reproducible.

## Problems worth reading about

- **Refund detection that couldn't fire.** JustGiving's API has no refund flag, so refunds are detected by a donation vanishing between pulls, using a dbt snapshot with `invalidate_hard_deletes`. A review found the snapshot's input was the accumulated raw history, so nothing could ever vanish from it. The fix reads only the newest complete pull per page, and it was proven live (remove a donation from a pull, watch it get invalidated and drop out of the mart, re-pull and watch it reopen). The design depends on every pull being complete, which rules out incremental fetching. Details in `dbt/snapshots/justgiving_donations_snapshot.sql`.
- **Four ways BigQuery's schema autodetect bit back.** A single test row with the name `"T"` typed a text column as boolean; a rate arriving as `0` before `0.43` typed it INTEGER; an all-digit ID clashed with an earlier STRING column; and `+0000` timestamps were rejected by strict parsing. The shared loader now keeps an existing table's types, and the connectors force fractional fields to float.
- **A 21× smaller upload.** On a slow connection the time went entirely to sending data, not to BigQuery. Compressing uploads cut 231 MB to 10.8 MB, a full load from hours to minutes. That change then silently corrupted emoji (JSON escaping split them into halves BigQuery couldn't store), caught through the dashboard and fixed with a test that fails on the old code.
- **A pagination parameter that silently did nothing.** JustGiving's v1 donations endpoint returns `200` but ignores `pageNumber`, so a naive loop re-reads page 1 forever. Found empirically and moved to v2.
- **`params={}` is not "no params".** On Instagram's cursor pagination, passing an empty dict to httpx replaced the URL's query string (and the access token with it), producing a 403 that looked like transient flakiness. Diagnosed properly instead of papering over it with retries.
- **A route guard with a blind spot.** After a framework upgrade, the test that checked every route had auth silently stopped seeing routes inside routers. It now also checks that the routes it walks equal the OpenAPI spec exactly, and calls every endpoint anonymously expecting a 401.
- **Metrics that look wrong if you aren't told why.** Instagram keeps post insights for two years, so an old post with lifetime likes but recent-only reach showed a 900% engagement rate; it is now withheld. Mailchimp opens are tracked by an image pixel, so junk-folder reads are undercounted while Apple Mail's pre-loading overcounts: clicks are the trustworthy signal, and the dashboard says so.

## Running it

Requires Python 3.12 managed by [uv](https://docs.astral.sh/uv/), a GCP project with BigQuery, and API credentials for whichever sources you want.

```bash
uv sync
cp .env.example .env              # fill in credentials
gcloud auth application-default login   # BigQuery auth, no key file needed

# refresh everything: all connectors, then dbt snapshot -> run -> test
uv run python -m ingestion.refresh

# or on a daily schedule (blocks, runs at 06:00 Europe/London)
uv run python -m ingestion.refresh --serve

# a single connector (run as a module, not by file path)
uv run python -m ingestion.mailchimp_campaigns

# dbt (uv-managed, not on PATH)
uv run dbt build --project-dir dbt --profiles-dir ~/.dbt
```

**Quickest way to see the dashboard:** `./demo.sh` starts the API on the synthetic demo data and the website together, opens http://localhost:3000 and prints the demo logins. It needs a GCP project with the synthetic dataset loaded (`uv run python -m synthetic.load`) and a Supabase project for logins. Ctrl+C stops both.

Dashboard (Next.js, in `web/`). It needs the API running; the Next.js server calls the API for the user, the browser never does:

```bash
uv run uvicorn main:app --port 8000      # API (BIGQUERY_DATASET=firasah_synthetic for demo data)
cd web && npm ci
cp .env.example .env.local               # Supabase URL + anon key, API URL
npm run dev                              # http://localhost:3000
npm run gen:api                          # regenerate TypeScript types after an API change
```

Checks (the same ones CI runs on every push, see `.github/workflows/ci.yml`):

```bash
uv run ruff check .          # lint
uv run ruff format --check . # formatting
uv run pytest                # 266 tests: ingestion helpers, auth attacks, tenant isolation, endpoint maths, synthetic data
uv run dbt parse --project-dir dbt --profiles-dir ci   # dbt project compiles, no warehouse needed
cd web && npm run lint && npm run typecheck && npm run build   # frontend
```

CI deliberately needs no secrets: unit tests use a fake HTTP transport and a fake warehouse instead of real services, and `dbt parse` never connects to BigQuery. Running the full `dbt build` in CI is a planned step (it needs a keyless GCP login via Workload Identity Federation).

One failing source doesn't stop the others: each connector is isolated, dbt runs on whatever landed, and the flow fails at the end naming the sources that broke. LaunchGood is only loaded when its export file has changed.

## Repo layout

```
ingestion/    connectors (one per source), shared retry/landing helpers, refresh flow
dbt/          staging, snapshots, intermediate, marts, tests and docs
api/          FastAPI auth, tenancy, query builder and dashboard endpoints
main.py       FastAPI app entry point
web/          Next.js dashboard (Supabase login, server-side API calls)
synthetic/    generator for three fake charities' raw data
supabase/     database migrations (membership table, row-level security, grants)
tests/        pytest suite
scripts/      one-off auth helpers and the live tenant-isolation check
ci/           placeholder dbt profile used by CI
CLAUDE.md     conventions, commands and architecture rules for coding agents and contributors
```

## Status

- **Done:** ingestion for all five sources, the modelling layers, dbt tests and docs, scheduled refresh.
- **Done:** FastAPI layer with per-charity data isolation, Supabase auth, synthetic multi-charity data.
- **Done:** the dashboard: Overview, Fundraising, Social, Email, Appeals and Data health pages, with loading, empty and error states.
- **Next:** deployment (Docker, GCP Cloud Run), then billing tiers.
- **Known limitations:** ingestion credentials are still single-charity (the data model and API are multi-charity); no currency conversion (the dashboard sums GBP only and reports how many other-currency donations it left out); LaunchGood refunds aren't detected; growth charts only have history from the first pull onwards; scheduling runs locally until deployment.

## Stack

Python · FastAPI · dbt · Prefect · BigQuery · Supabase (auth) · Next.js · Recharts · GitHub Actions. Planned: Docker · GCP Cloud Run · Stripe.

## Licence

Source-available under the [PolyForm Noncommercial License 1.0.0](LICENSE). You are welcome to read, run and learn from the code, including to evaluate it as a piece of work. Commercial use is not permitted without a separate agreement; get in touch if you want one.
