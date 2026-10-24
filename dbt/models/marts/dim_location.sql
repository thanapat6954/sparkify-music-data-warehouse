-- Keep the source location string. Do not infer precise city/country coordinates.
select distinct md5(coalesce(location, 'unknown')) as location_key,
    coalesce(location, 'unknown') as location
from {{ ref('stg_events') }}
