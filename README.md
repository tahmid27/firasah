# Firasah

An analytics platform for UK charities. Charities raise money and build audiences across a scatter of platforms that don't talk to each other. A fundraising manager who wants to know "did that Instagram push actually move donations?" currently exports several CSVs and fights a spreadsheet.

Firasah pulls those sources into one warehouse on a schedule, models them into tables that mean the same thing across platforms, and (in progress) serves dashboards on top.

| Area | Sources |
| --- | --- |
| Fundraising | JustGiving (API), LaunchGood (manual CSV export, since it has no public API) |
| Social | Instagram (Graph API), TikTok (Content API) |
| Email | Mailchimp (API) |

This is a solo project built as portfolio evidence for analytics engineering work, so the emphasis is on the data platform: connector design, warehouse modelling, testing, and decisions that can be defended. Commercial traction is not the goal.

## Architecture

```
  JustGiving API ─┐
      TikTok API ─┤   ingestion/*.py        raw_* tables             dbt
   Mailchimp API ─┼─► (shared common.py) ─►  BigQuery    ─►  staging (views)
  LaunchGood CSV ─┤    Prefect flows         append-only             │
   Instagram API ─┘                       schema autodetect          ▼
                                                                 snapshot
                                                          (change + deletions)
                                                                     │
                                                                     ▼
                                                    intermediate (cross-source unions)
                                                                     │
                                                                     ▼
                                                        marts (fct_ tables)
                                                                     │
                                                                     ▼
                                                  FastAPI ──► Next.js dashboard   (planned)
```

Three ideas hold it together:

1. **Raw is append-only and untouched.** Nothing is renamed, cast, filtered or deduplicated on the way in. Every run appends a full pull tagged with when it arrived. If the cleaning logic turns out wrong, fix the model and rebuild; never re-pull from the API.
2. **All cleaning is SQL, in dbt, in version control.**
3. **Each layer has one job.** Staging renames and casts. Snapshots track change over time. Intermediate models unify sources. Marts answer business questions.

## Data model

| Mart | Grain | Notes |
| --- | --- | --- |
| `fct_donations` | one row per donation, JustGiving + LaunchGood | refund-aware on the JustGiving side |
| `fct_social_posts` | one row per post, Instagram + TikTok | latest-known stats per post |
| `fct_social_account_stats` | one row per account per ingestion run | deliberately not deduplicated: the history is what makes a follower-growth chart possible |
| `fct_mailchimp_campaigns` | one row per sent campaign | latest-known stats |
| `fct_mailchimp_audience_stats` | one row per audience per ingestion run | kept as history, like the social account stats |

Where only one platform offers a metric (TikTok views, LaunchGood Zakat amount), the unified table keeps the column and leaves the other platform's rows null rather than dropping the data.

Tests: `not_null`, `unique`, `accepted_values` and `relationships` tests across the layers (50+ in total), plus generated dbt docs.

## Problems worth reading about

- **Refund detection that couldn't fire.** JustGiving's API has no refund flag, so refunds are detected by a donation vanishing between pulls, using a dbt snapshot with `invalidate_hard_deletes`. A review found the snapshot's input was the accumulated raw history, so nothing could ever vanish from it. The fix reads only the newest complete pull per page, and it was proven live (remove a donation from a pull, watch it get invalidated and drop out of the mart, re-pull and watch it reopen). The design depends on every pull being complete, which rules out incremental fetching. Details in `dbt/snapshots/justgiving_donations_snapshot.sql`.
- **A pagination parameter that silently did nothing.** JustGiving's v1 donations endpoint returns `200` but ignores `pageNumber`, so a naive loop re-reads page 1 forever. Found empirically and moved to v2.
- **`params={}` is not "no params".** On Instagram's cursor pagination, passing an empty dict to httpx replaced the URL's query string (and the access token with it), producing a 403 that looked like transient flakiness. Diagnosed properly instead of papering over it with retries.
- **Schema autodetect from one odd row.** A single LaunchGood test row with the display name `"T"` made BigQuery infer the whole column as boolean.
- **Open rates that lie in both directions.** Mailchimp opens are tracked by an image pixel, so emails read in a junk folder (images blocked) are undercounted, while Apple Mail's pre-loading overcounts. Clicks are the trustworthy signal; the raw data keeps the Apple-excluded rate for this reason.

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

One failing source doesn't stop the others: each connector is isolated, dbt runs on whatever landed, and the flow fails at the end naming the sources that broke. LaunchGood is only loaded when its export file has changed.

## Repo layout

```
ingestion/    connectors (one per source), shared retry/landing helpers, refresh flow
dbt/          staging, snapshots, intermediate, marts, tests and docs
scripts/      one-off auth helpers (token exchanges), not part of the pipeline
main.py       FastAPI app (health check only so far)
CLAUDE.md     working notes and decision log, with dates and reasoning
```

## Status

- **Done:** ingestion for all five sources, the modelling layers, tests and docs, scheduled refresh.
- **Next:** FastAPI layer with per-charity data isolation, then the dashboard (Next.js + Recharts).
- **Later:** billing, deployment, and an agent layer for weekly reports.
- **Known limitations:** single-charity today; no currency conversion (test data is all GBP); LaunchGood refunds aren't detected yet; growth charts only have history from the first pull onwards; scheduling runs locally until deployment.

## Stack

Python · FastAPI · dbt · Prefect · BigQuery · Supabase (auth) · Next.js · Recharts · Docker · GCP Cloud Run
