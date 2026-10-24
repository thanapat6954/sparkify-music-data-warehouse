select t.iso_weekday, t.hour_utc, t.daypart_utc,
    count(*) as songplays, sum(f.played_track_duration_seconds) / 3600.0 as played_track_hours
from {{ ref('fact_user_events') }} f join {{ ref('dim_time') }} t on f.time_key = t.time_key
where f.is_songplay = 1 group by t.iso_weekday, t.hour_utc, t.daypart_utc
