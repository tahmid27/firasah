-- Table privileges aren't granted automatically on this project; RLS still
-- decides which rows each role sees. anon stays with none.

grant select on table public.organisations, public.memberships to authenticated;

grant select, insert, update, delete
    on table public.organisations, public.memberships
    to service_role;
