select event_id from {{ ref('fact_user_events') }}
where played_track_duration_seconds < 0 or (is_songplay = 1 and played_track_duration_seconds is null)
