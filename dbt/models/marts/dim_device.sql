select distinct md5(coalesce(user_agent, 'unknown')) as device_key,
    user_agent, device_family, browser_family
from {{ ref('stg_events') }}
