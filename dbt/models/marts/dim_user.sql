-- Type 1 attributes. Free/Paid history lives in dim_user_subscription.
with ranked as (
    select user_id, gender, location,
        min(event_ts) over(partition by user_id) as first_seen,
        row_number() over(partition by user_id order by event_ts desc, event_id desc) as rn
    from {{ ref('stg_events') }} where user_id is not null
)
select user_id as user_key, gender, location as latest_location, first_seen
from ranked where rn = 1
union all
select 'unknown', null, null, cast(null as timestamp)
