select 'event_count' as failure
where (select count(*) from {{ ref('fact_user_events') }}) <> (select count(*) from {{ ref('stg_events') }})
union all
select 'songplay_count' where
    (select sum(is_songplay) from {{ ref('fact_user_events') }}) <>
    (select count(*) from {{ ref('stg_events') }} where page = 'NextSong')
union all
select 'duration' where abs(
    (select coalesce(sum(played_track_duration_seconds),0) from {{ ref('fact_user_events') }}) -
    (select coalesce(sum(length_seconds),0) from {{ ref('stg_events') }} where page = 'NextSong')) > 0.0001
