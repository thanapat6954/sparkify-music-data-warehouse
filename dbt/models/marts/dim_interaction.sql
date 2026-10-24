select distinct page as interaction_key, page,
    case when page = 'NextSong' then 'streaming'
         when page in ('Upgrade','Submit Upgrade','Downgrade','Submit Downgrade') then 'subscription'
         when page = 'Error' then 'error' else 'navigation' end as interaction_group
from {{ ref('stg_events') }}
