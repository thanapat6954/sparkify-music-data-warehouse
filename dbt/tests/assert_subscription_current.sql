select user_id from {{ ref('dim_user_subscription') }}
group by user_id having sum(case when is_current then 1 else 0 end) <> 1
