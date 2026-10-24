select event_date, subscription_key, sum(is_songplay) as songplays,
    sum(played_track_duration_seconds) / 3600.0 as played_track_hours
from {{ ref('fact_user_events') }} group by event_date, subscription_key
