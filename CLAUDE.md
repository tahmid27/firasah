# Firasah: project context for coding agents

Firasah is an analytics platform for UK charities. It pulls fundraising, social and email data (JustGiving, LaunchGood, Instagram, TikTok, Mailchimp) into BigQuery, models it with dbt, and serves per-charity dashboards through a FastAPI service and a Next.js app. See [README.md](README.md) for the architecture and the reasoning behind it.

A fuller, private decision log is kept outside the repo. This file holds only the stable conventions and commands.

## Stack

Python 3.12 (managed by `uv`) · FastAPI · dbt (BigQuery) · Prefect · Supabase (auth, Postgres row-level security) · Next.js 16 + Recharts · GitHub Actions. Planned: Docker, GCP Cloud Run, Stripe.

## Commands

- **Checks before committing** (CI runs the same): `uv run ruff check . && uv run ruff format --check . && uv run pytest`. `uv run ruff format .` fixes formatting.
- **dbt is uv-managed, not on PATH.** From the repo root: `uv run dbt <command> --project-dir dbt --profiles-dir ~/.dbt`. CI uses `--profiles-dir ci` with `dbt parse`, which needs no warehouse.
- **Connectors are a package: run with `-m`**, e.g. `uv run python -m ingestion.mailchimp_campaigns`. Running a file by path fails with `ModuleNotFoundError`.
- **Whole refresh:** `uv run python -m ingestion.refresh` (add `--serve` for the daily schedule).
- **API:** `uv run uvicorn main:app --port 8000`. **Dashboard:** `cd web && npm ci && npm run dev`. After changing the API, run `npm run gen:api` in `web/` to regenerate the TypeScript types (CI fails if they are stale).
- **Demo:** `./demo.sh` starts the API on the synthetic dataset and the dashboard together.
- **Synthetic data:** `uv run python -m synthetic.load` regenerates and loads three fake charities into a dataset whose name ends in `_synthetic`.
- **BigQuery auth** uses Application Default Credentials (`gcloud auth application-default login`), with the project set by `GOOGLE_CLOUD_PROJECT`. Make sure no stale `GOOGLE_APPLICATION_CREDENTIALS` is set in the shell: it silently overrides ADC.

## Architecture rules (do not break these)

1. **Raw tables are append-only and untouched.** Renaming, casting, filtering and deduplication happen in dbt, never at ingestion.
2. **Layers:** staging renames and casts (one file per raw table); snapshots track change; intermediate models unify sources; marts (`fct_`, `dim_`) answer business questions.
3. **Tenant isolation.** Every raw row carries `_org_id`; every staging model, dedup, join and snapshot key includes `org_id`. In the API, `org_id` comes only from the verified token plus a server-side membership lookup, never from request parameters, bodies or headers. All BigQuery access goes through the query builder in `api/warehouse.py`, which adds `WHERE org_id = @org_id` to every query. Another charity's resource returns 404, not 403. Tests enforce all of this; do not weaken them to make a change pass.
4. **Every API endpoint declares a Pydantic `response_model`**, so credential-shaped fields can never be serialised out.
5. **Snapshots rely on complete pulls.** JustGiving refund detection treats a donation vanishing from the newest complete pull as a refund, so never switch that connector to incremental fetching.
6. **Fields that are fractional but can arrive as whole numbers** (rates, percentages, money) must go through `coerce_to_float` in the connector, because BigQuery schema autodetect types a column from its first values.
7. **Never log error messages from HTTP calls.** URLs in them can carry access tokens; log the error type and status only.
8. **Synthetic data starts at the raw layer**, in the real APIs' shapes, and runs through the real connectors' parsing code and every dbt model. Never fake mart tables directly.

## Conventions

- **Commits:** conventional commits (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `perf:`).
- **Naming:** kebab-case for files, branches and the repo; snake_case for Python and SQL.
- **Scope:** work through the roadmap in order; do not pull later-phase work forward unless asked.
- **UI wording:** say "donations", not "gifts" (the product term "Gift Aid" is unchanged).
- **Comments:** keep them brief; explanations belong in commit messages and the README.
- **Secrets** live in `.env` (gitignored; `.env.example` lists the names). Never commit credentials, tokens or real charity data.

## Roadmap

1. Foundations and scaffolding: done
2. First vertical slice (JustGiving to a mart): done
3. Multi-source data layer: done
4. Backend API with tenant isolation: done
5. Dashboard frontend: done
6. Billing and subscription tiers (Stripe): not started
7. Deployment (Docker, Cloud Run, CI/CD, monitoring, first beta charity): not started
8. Agentic layer (weekly reports, campaign chase-ups): not started
