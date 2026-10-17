-- Tenancy core: which charities exist, and which user belongs to which one.
--
-- RLS (Row Level Security) = the database itself filters rows by who is
-- asking, so even a bug in the API can't hand out another charity's rows.
-- Two Supabase facts drive this file:
--   * Any table in `public` WITHOUT RLS is readable by anyone holding the
--     anon key, which ships to every browser. So RLS is enabled on both.
--   * The service-role key bypasses RLS entirely. Writes here are meant to
--     happen only through it (server-side), so there are deliberately NO
--     insert/update/delete policies: logged-in users can read, never write.

-- ---------------------------------------------------------------------------
-- organisations: one row per charity (tenant)
-- ---------------------------------------------------------------------------
create table public.organisations (
    -- Same format the ingestion layer enforces on every BigQuery row
    -- (ingestion validate_org_id): readable dev IDs like "test_charity" and
    -- generated UUIDs both fit. Text, not uuid, so both coexist.
    id text primary key
        check (id ~ '^[a-z0-9][a-z0-9_-]{1,63}$'),
    name text not null,
    created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- memberships: which user belongs to which charity, and their role
-- ---------------------------------------------------------------------------
create table public.memberships (
    -- user_id as the PRIMARY KEY is what enforces "one charity per user"
    -- (decided 2026-10-17): the database refuses a second membership row
    -- for the same user. Moving to several charities per user later means
    -- changing this key to (user_id, org_id) plus an "active org" choice.
    user_id uuid primary key references auth.users (id) on delete cascade,
    org_id text not null references public.organisations (id) on delete cascade,
    role text not null default 'member' check (role in ('admin', 'member')),
    created_at timestamptz not null default now()
);

create index memberships_org_id_idx on public.memberships (org_id);

-- ---------------------------------------------------------------------------
-- Row Level Security
-- ---------------------------------------------------------------------------
alter table public.organisations enable row level security;
alter table public.memberships enable row level security;

-- A logged-in user can see their own membership row, and nobody else's.
-- (select auth.uid()) rather than auth.uid() lets Postgres evaluate it once
-- per query instead of once per row (Supabase's recommended form).
create policy "users read their own membership"
    on public.memberships
    for select
    to authenticated
    using (user_id = (select auth.uid()));

-- A logged-in user can see the organisation they belong to, and no other.
create policy "members read their own organisation"
    on public.organisations
    for select
    to authenticated
    using (
        exists (
            select 1
            from public.memberships m
            where m.org_id = organisations.id
              and m.user_id = (select auth.uid())
        )
    );

-- Belt and braces: anonymous (not logged in) callers get no privileges at
-- all on these tables, even before RLS is consulted.
revoke all on table public.organisations from anon;
revoke all on table public.memberships from anon;

-- ---------------------------------------------------------------------------
-- Dev tenant, matching FIRASAH_ORG_ID and the rows already in BigQuery
-- ---------------------------------------------------------------------------
insert into public.organisations (id, name)
values ('test_charity', 'Test Charity');
