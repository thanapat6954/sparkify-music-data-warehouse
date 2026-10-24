-- Observed engagement decline. No calibrated churn probability or churn label.
with bounds as (
    select max(event_date) as as_of_date, min(event_date) as first_dataset_date from {{ ref('fact_user_events') }}
), features as (
    select d.user_key, b.as_of_date,
        {{ days_between('b.as_of_date', 'cast(u.first_seen as date)') }} + 1 as observed_days,
        sum(case when {{ days_between('b.as_of_date', 'd.event_date') }} between 0 and 6 then d.songplays else 0 end) as current_7d_songplays,
        sum(case when {{ days_between('b.as_of_date', 'd.event_date') }} between 7 and 13 then d.songplays else 0 end) as prior_7d_songplays,
        {{ days_between('b.as_of_date', 'max(case when d.songplays > 0 then d.event_date end)') }} as days_since_last_songplay
    from {{ ref('fact_user_day') }} d cross join bounds b
    join {{ ref('dim_user') }} u on d.user_key = u.user_key
    group by d.user_key, b.as_of_date, u.first_seen
)
select *,
    case when observed_days >= 14 and prior_7d_songplays >= 5
        then 1.0 - current_7d_songplays * 1.0 / prior_7d_songplays end as songplay_decline_fraction,
    case when observed_days < 14 then 'insufficient_history'
         when prior_7d_songplays >= 5 and current_7d_songplays <= prior_7d_songplays * 0.5 then 'engagement_decline'
         when days_since_last_songplay >= 7 then 'inactive_7d'
         else 'no_rule_trigger' end as watchlist_reason,
    'unvalidated_engagement_rule' as interpretation
from features
