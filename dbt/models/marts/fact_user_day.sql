-- Dense periodic snapshot: retain inactive days after a user's first observation.
with recursive bounds as (
    select min(event_date) as min_date, max(event_date) as max_date from {{ ref('dim_time') }}
), dates(event_date) as (
    select min_date from bounds where min_date is not null
    union all
    select cast(d.event_date + interval '1 day' as date) from dates d cross join bounds b
    where d.event_date < b.max_date
), grid as (
    select u.user_key, d.event_date from {{ ref('dim_user') }} u cross join dates d
    where u.user_key <> 'unknown' and d.event_date >= cast(u.first_seen as date)
), activity as (
    select user_key, event_date, count(*) as events, sum(is_songplay) as songplays,
        count(distinct session_id) as sessions,
        sum(played_track_duration_seconds) as played_track_duration_seconds,
        sum(is_upgrade_submission) as upgrade_submissions,
        sum(is_downgrade_submission) as downgrade_submissions
    from {{ ref('fact_user_events') }} where user_key <> 'unknown'
    group by user_key, event_date
)
select g.*, coalesce(a.events, 0) as events, coalesce(a.songplays, 0) as songplays,
    coalesce(a.sessions, 0) as sessions,
    coalesce(a.played_track_duration_seconds, 0) as played_track_duration_seconds,
    coalesce(a.upgrade_submissions, 0) as upgrade_submissions,
    coalesce(a.downgrade_submissions, 0) as downgrade_submissions
from grid g left join activity a on g.user_key = a.user_key and g.event_date = a.event_date
