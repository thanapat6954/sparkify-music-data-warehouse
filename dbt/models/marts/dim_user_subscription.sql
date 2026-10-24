select * from {{ ref('int_subscription_history') }}
union all
select 'unknown', 'unknown', 'unknown', cast(null as timestamp), cast(null as timestamp), true
