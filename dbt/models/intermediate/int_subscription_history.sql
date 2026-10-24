-- Reconstruct effective membership from observed event states, not load time.
with previous as (
    select user_id, membership_level, event_ts, event_id,
        lag(membership_level) over(partition by user_id order by event_ts, event_id) as previous_level
    from {{ ref('stg_events') }} where user_id is not null
), changes as (
    select * from previous
    where previous_level is null or previous_level <> membership_level
), intervals as (
    select user_id, membership_level, event_ts as valid_from,
        lead(event_ts) over(partition by user_id order by event_ts, event_id) as valid_to
    from changes
)
select md5(user_id || ':' || cast(valid_from as varchar)) as subscription_history_key,
    *, valid_to is null as is_current
from intervals
