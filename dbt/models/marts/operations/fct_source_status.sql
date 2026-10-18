-- One row per org per data source: when its data last landed, and how its
-- most recent refresh run went.
with heartbeats as (

    -- A table every successful run of that connector loads
    select org_id, 'justgiving' as source, max(ingested_at) as last_data_at
    from {{ ref('stg_justgiving_pages') }} group by org_id
    union all
    select org_id, 'launchgood', max(ingested_at)
    from {{ ref('stg_launchgood_donations') }} group by org_id
    union all
    select org_id, 'instagram', max(ingested_at)
    from {{ ref('stg_instagram_account_info') }} group by org_id
    union all
    select org_id, 'tiktok', max(ingested_at)
    from {{ ref('stg_tiktok_user_info') }} group by org_id
    union all
    select org_id, 'mailchimp', max(ingested_at)
    from {{ ref('stg_mailchimp_audience_stats') }} group by org_id

),

last_run as (

    select *
    from {{ ref('stg_refresh_runs') }}
    qualify row_number() over (partition by org_id, source order by started_at desc) = 1

),

last_success as (

    select org_id, source, max(finished_at) as last_success_at
    from {{ ref('stg_refresh_runs') }}
    where status = 'success'
    group by org_id, source

)

select
    org_id,
    source,
    heartbeats.last_data_at,
    last_run.started_at as last_run_at,
    last_run.status as last_run_status,
    last_run.error_type as last_error_type,
    last_run.http_status as last_http_status,
    last_success.last_success_at

from heartbeats
full outer join last_run using (org_id, source)
left join last_success using (org_id, source)
