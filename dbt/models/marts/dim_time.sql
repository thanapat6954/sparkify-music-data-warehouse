select distinct event_ts as time_key, event_date,
    cast(extract(year from event_ts) as integer) as year,
    cast(extract(month from event_ts) as integer) as month,
    cast(extract(week from event_ts) as integer) as iso_week,
    cast(extract(isoyear from event_ts) as integer) as iso_year,
    cast(extract(isodow from event_ts) as integer) as iso_weekday,
    cast(extract(hour from event_ts) as integer) as hour_utc,
    extract(isodow from event_ts) in (6,7) as is_weekend,
    case when extract(hour from event_ts) < 6 then 'night'
         when extract(hour from event_ts) < 12 then 'morning'
         when extract(hour from event_ts) < 18 then 'afternoon' else 'evening' end as daypart_utc
from {{ ref('stg_events') }}
