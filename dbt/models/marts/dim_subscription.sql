select distinct membership_level as subscription_key, membership_level
from {{ ref('stg_events') }}
