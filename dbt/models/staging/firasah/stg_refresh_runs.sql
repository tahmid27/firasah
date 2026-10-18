with raw as (

    select * from {{ source('firasah', 'raw_refresh_runs') }}

),

renamed as (

    select
        _org_id as org_id,
        source,
        status,
        started_at,
        finished_at,
        error_type,
        http_status,
        _ingested_at as ingested_at
    from raw

)

select * from renamed
