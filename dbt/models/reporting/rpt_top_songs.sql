with counts as (
    select t.daypart_utc, s.song_title, s.artist_name, count(*) as songplays
    from {{ ref('fact_user_events') }} f join {{ ref('dim_time') }} t on f.time_key = t.time_key
    join {{ ref('dim_song') }} s on f.song_key = s.song_key
    where f.is_songplay = 1 group by t.daypart_utc, s.song_title, s.artist_name
)
select *, row_number() over(partition by daypart_utc order by songplays desc, artist_name, song_title) as song_rank
from counts
