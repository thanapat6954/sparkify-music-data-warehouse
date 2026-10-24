select user_key, event_date from {{ ref('fact_user_day') }}
group by user_key, event_date having count(*) <> 1
