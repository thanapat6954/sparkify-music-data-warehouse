with counts as (
    select t.daypart_utc, a.artist_name, count(*) as songplays
    from {{ ref('fact_user_events') }} f join {{ ref('dim_time') }} t on f.time_key = t.time_key
    join {{ ref('dim_artist') }} a on f.artist_key = a.artist_key
    where f.is_songplay = 1 group by t.daypart_utc, a.artist_name
)
select *, row_number() over(partition by daypart_utc order by songplays desc, artist_name) as artist_rank
from counts
