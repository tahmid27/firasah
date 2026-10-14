-- One row per donation across every fundraising platform (JustGiving +
-- LaunchGood), ready to chart. "Currently-active" / refund-aware only has
-- real teeth on the JustGiving side so far — see int_donations_unioned for
-- why LaunchGood doesn't have the same guarantee yet.
select * from {{ ref('int_donations_unioned') }}
