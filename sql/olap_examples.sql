-- Roll-up from month/level to month subtotal and grand total.
select cast(date_trunc('month', event_ts) as date) as month, subscription_key,
    grouping(cast(date_trunc('month', event_ts) as date)) as is_all_months,
    grouping(subscription_key) as is_all_levels,
    sum(is_songplay) as songplays
from analytics.fact_user_events
group by rollup(cast(date_trunc('month', event_ts) as date), subscription_key);

-- Slice & dice: Paid songplays on weekends, drill down to artist.
select t.daypart_utc, a.artist_name, count(*) as songplays
from analytics.fact_user_events f
join analytics.dim_time t on f.time_key = t.time_key
join analytics.dim_artist a on f.artist_key = a.artist_key
where f.subscription_key='paid' and t.is_weekend and f.is_songplay=1
group by t.daypart_utc, a.artist_name order by songplays desc;

-- Membership history: half-open effective intervals.
select user_id, membership_level, valid_from, valid_to, is_current
from analytics.dim_user_subscription
where user_id <> 'unknown' order by user_id, valid_from;
