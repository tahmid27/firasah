-- Tenancy core: charities (organisations) and which user belongs to which.
-- Writes go through the service role only, so there are no insert/update/
-- delete policies.

create table public.organisations (
    -- Same format as core/org_ids.py
    id text primary key
        check (id ~ '^[a-z0-9][a-z0-9_-]{1,63}$'),
    name text not null,
    created_at timestamptz not null default now()
);

create table public.memberships (
    -- Primary key on user_id: one charity per user
    user_id uuid primary key references auth.users (id) on delete cascade,
    org_id text not null references public.organisations (id) on delete cascade,
    role text not null default 'member' check (role in ('admin', 'member')),
    created_at timestamptz not null default now()
);

create index memberships_org_id_idx on public.memberships (org_id);

alter table public.organisations enable row level security;
alter table public.memberships enable row level security;

create policy "users read their own membership"
    on public.memberships
    for select
    to authenticated
    using (user_id = (select auth.uid()));

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

revoke all on table public.organisations from anon;
revoke all on table public.memberships from anon;

-- Dev tenant, matching FIRASAH_ORG_ID
insert into public.organisations (id, name)
values ('test_charity', 'Test Charity');
