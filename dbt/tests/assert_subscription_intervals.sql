with intervals as (
    select *, lag(valid_to) over(partition by user_id order by valid_from) as previous_valid_to,
        row_number() over(partition by user_id order by valid_from) as rn
    from {{ ref('dim_user_subscription') }} where user_id <> 'unknown'
)
select subscription_history_key from intervals
where valid_to <= valid_from or (rn > 1 and previous_valid_to <> valid_from)
