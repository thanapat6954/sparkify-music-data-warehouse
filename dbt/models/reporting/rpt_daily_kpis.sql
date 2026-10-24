select event_date, count(*) as events, sum(is_songplay) as songplays,
    count(distinct case when is_songplay = 1 and user_key <> 'unknown' then user_key end) as dau,
    sum(played_track_duration_seconds) / 3600.0 as played_track_hours,
    sum(is_upgrade_submission) as upgrade_submissions,
    sum(is_downgrade_submission) as downgrade_submissions
from {{ ref('fact_user_events') }} group by event_date
