select 'songplays' as failure where
    (select sum(songplays) from {{ ref('fact_user_day') }}) <>
    (select sum(is_songplay) from {{ ref('fact_user_events') }} where user_key <> 'unknown')
union all
select 'duration' where abs(
    (select sum(played_track_duration_seconds) from {{ ref('fact_user_day') }}) -
    (select sum(played_track_duration_seconds) from {{ ref('fact_user_events') }} where user_key <> 'unknown')) > 0.0001
