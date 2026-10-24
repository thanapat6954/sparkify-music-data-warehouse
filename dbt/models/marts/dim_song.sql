with observed as (
    select distinct song, artist
    from {{ ref('stg_events') }} where song is not null and artist is not null
), catalog as (
    select title, artist_name, count(*) as matches,
        min(song_id) as song_id, min(year) as year, min(duration) as duration
    from {{ ref('stg_songs') }} group by title, artist_name
)
select md5(o.artist || chr(31) || o.song) as song_key, o.song as song_title,
    o.artist as artist_name, md5(o.artist) as artist_key,
    case when c.matches = 1 then c.song_id end as catalog_song_id,
    case when c.matches = 1 then nullif(c.year, 0) end as release_year,
    case when c.matches = 1 then c.duration end as catalog_duration_seconds,
    case when c.matches = 1 then 'exact_unique' when c.matches > 1 then 'ambiguous' else 'unmatched' end as catalog_match_status
from observed o left join catalog c on o.song = c.title and o.artist = c.artist_name
union all select 'unknown', 'unknown', 'unknown', 'unknown', null, null, null, 'not_applicable'
