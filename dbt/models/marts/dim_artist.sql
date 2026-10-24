select distinct md5(artist) as artist_key, artist as artist_name
from {{ ref('stg_events') }} where artist is not null
union all select 'unknown', 'unknown'
