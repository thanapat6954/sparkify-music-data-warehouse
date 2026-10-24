-- DAU by UTC calendar day.
select event_date, dau, songplays, played_track_hours
from analytics.rpt_daily_kpis order by event_date;

-- MAU: distinct users in a month, never sum daily distinct counts.
select * from analytics.rpt_monthly_kpis order by month;

-- Share of played track lengths, not measured actual listening hours.
select subscription_key, sum(played_track_hours) as played_track_hours,
    sum(played_track_hours) / nullif(sum(sum(played_track_hours)) over(), 0) as share
from analytics.rpt_listening_by_membership group by subscription_key;

-- Heatmap for all observed data; UTC weekday/hour.
select iso_weekday, hour_utc, songplays from analytics.rpt_listening_heatmap;

select daypart_utc, artist_name, songplays, artist_rank
from analytics.rpt_top_artists where artist_rank <= 10 order by daypart_utc, artist_rank;

select daypart_utc, song_title, artist_name, songplays, song_rank
from analytics.rpt_top_songs where song_rank <= 10 order by daypart_utc, song_rank;

-- Restricted local BI view; treat identifiers as pseudonymous account data.
select md5(user_key) as user_pseudonym, as_of_date, prior_7d_songplays,
    current_7d_songplays, songplay_decline_fraction, days_since_last_songplay, watchlist_reason
from analytics.rpt_engagement_watchlist
where watchlist_reason in ('engagement_decline','inactive_7d')
order by watchlist_reason, songplay_decline_fraction desc;

-- Date-filtered top artists: change literals for your chosen UTC interval.
select a.artist_name, count(*) as songplays
from analytics.fact_user_events f join analytics.dim_artist a on f.artist_key = a.artist_key
where f.is_songplay = 1 and f.event_date >= date '2018-11-01' and f.event_date < date '2018-12-01'
group by a.artist_name order by songplays desc, a.artist_name limit 10;
