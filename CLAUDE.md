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

## Roadmap

Eight-phase build: Foundations → MVP → Agentic AI layer. Full roadmap lives in a separate tracker app outside this repo.

**Current phase:** Foundations — Python environment set up with uv (Python 3.12, pyproject.toml + uv.lock). Core dependencies pinned: fastapi, dbt-core, dbt-bigquery. dbt project at `dbt/` (profile `firasah`, BigQuery target `firasah-dev`/`firasah_dev` in europe-west2), connection verified via `dbt debug`. Note: `dbt` is uv-managed, not on PATH directly — invoke as `uv run dbt <command> --project-dir dbt --profiles-dir ~/.dbt` from repo root.

First data pipeline slice built end to end: `dbt/seeds/justgiving_donations.csv` (28 rows of sample JustGiving donation data, deliberately raw/inconsistent column names) → `stg_justgiving_donations` staging model (`dbt/models/staging/justgiving/`, renames + casts types, materialized as a view via `+materialized: view` on the `staging` folder in `dbt_project.yml`) → schema tests (`not_null` on core columns, `unique` + `not_null` on `donation_id`). `dbt seed`, `dbt run`, `dbt test` all pass. No marts, no other sources, no app code, no Prefect flows yet — next step is either another source's staging model (LaunchGood, Instagram, etc.) or the first FastAPI routes.

**Learning approach:** dbt Fundamentals course started but not finished
(modules 1-2 done; 3, 4, 6 pending). Building ahead of course completion
deliberately — Claude Code is expected to directly teach core dbt concepts
during build sessions rather than assume course knowledge, then course
modules get done afterward to consolidate/fill gaps, not as a gate before
building. Covered so far in build sessions: seeds vs sources (seeds are
loaded by dbt itself via `dbt seed` and referenced with `ref()`; sources
are raw data landed by something outside dbt and referenced with
`source()`), what a model is (a `.sql` file with a `SELECT`, compiled by
dbt), materializations (view vs table), why staging models exist
(rename/cast only, no business logic, one file per source table),
and generic tests (`not_null`, `unique`) declared in schema `.yml` files.
Not yet covered: snapshots, incremental models, intermediate/mart layers,
packages, macros.

Update this line at the start of any session where the phase or learning stage has moved on, so the next session starts oriented correctly. Example: `"Learned dbt staging models + sources this week — applying that now to the first JustGiving data source. Not yet covered: tests, snapshots, incremental models."`

## Conventions

- **Commits:** Conventional commits (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`). Every session ends in a real commit — even an unfinished feature gets committed with a clear message, not left dangling locally.
- **Naming:** kebab-case for files, branches, and the repo itself.
- **Gitignore:** Python + Node coverage — `.env`, `__pycache__`, `node_modules`, `.idea`, `.vscode` — already in place; keep it current as new tooling gets added.
- **Scope discipline:** stay inside the current phase. Don't pull forward work from later phases (e.g. don't wire up Stripe during the Foundations phase) unless explicitly asked.

## Learning & explanation preferences

The person building this wants to genuinely understand the infrastructure they're shipping — this project is proof of skill, not just proof of output — but has a limited weekly learning budget and doesn't want to burn it memorizing boilerplate or syntax that carries no transferable understanding.

**When generating non-trivial code, flag what's actually worth understanding versus what's just implementation detail.** Concretely:

**Worth flagging (call these out explicitly, briefly):**
- Architectural decisions and *why* one approach was chosen over an alternative (e.g. why a staging/intermediate/mart layering in dbt, why Prefect handles retries a certain way, why an endpoint is structured a particular way)
- Design patterns that will recur elsewhere in the codebase or come up in interviews (auth flow logic, pipeline orchestration structure, data modeling choices, API design decisions)
- Anything that trades off cost, performance, or maintainability in a way a technical interviewer might probe
- Non-obvious gotchas specific to this stack (BigQuery quirks, dbt materialization choices, Supabase auth edge cases)

**Not worth flagging (skip silently, no need to explain):**
- Standard library usage, common syntax, boilerplate CRUD
- Repetitive config or scaffolding that follows a pattern already established once
- Verbose type hints or framework conventions that are just "how FastAPI/Next.js expects things structured"
- Anything where understanding it wouldn't transfer to a different tool or a job interview

**How to surface it:** end a meaningful chunk of work with a short "Worth understanding" callout — 2–4 bullet points max, plain language, no lecture. Not inline comments cluttering the code, and not a dense essay. If nothing in a given chunk clears the bar above, skip the callout entirely rather than padding it out.

**Keep the language genuinely simple, not just short.** Most of this stack (dbt, BigQuery, uv, general backend/data infra) is being learned for the first time — write each bullet like you're explaining it to a smart friend with no background in that specific tool, not a peer engineer. Don't stack multiple unexplained technical terms in one sentence. If a technical term is needed, explain what it means in the same breath instead of assuming familiarity. A plain sentence that's slightly less precise beats a dense one that's exactly right but hard to follow. This isn't being saved for later study — it just needs to land in the moment.

## Not doing yet / explicitly deferred

- Stripe integration — not until MVP phase
- Agentic AI layer — final phase, not before the rest is solid
- Deep hands-on depth on tools outside the core stack (e.g. Databricks/Spark) — conceptual fluency mapped to BigQuery/dbt experience is sufficient; not worth build time given the job-search timeline

## Keeping this file current

When a real architectural decision gets made, a phase completes, or the stack changes — update the relevant section above in the same session. Don't let this file drift out of sync with what's actually true of the codebase.

## Session wrap-up

Before ending a session where real progress was made, update the "Current
phase" / learning-progress section above to reflect what was actually
covered and built — don't wait to be asked if it's obviously out of date.

