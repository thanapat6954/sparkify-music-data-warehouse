select cast(date_trunc('month', event_ts) as date) as month,
    count(distinct case when is_songplay = 1 and user_key <> 'unknown' then user_key end) as mau,
    sum(is_songplay) as songplays,
    sum(played_track_duration_seconds) / 3600.0 as played_track_hours
from {{ ref('fact_user_events') }} group by cast(date_trunc('month', event_ts) as date)
