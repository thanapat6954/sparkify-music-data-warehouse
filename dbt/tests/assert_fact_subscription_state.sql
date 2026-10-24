select f.event_id from {{ ref('fact_user_events') }} f
join {{ ref('dim_user_subscription') }} h on f.subscription_history_key = h.subscription_history_key
where f.user_key <> 'unknown' and (f.subscription_key <> h.membership_level
    or f.event_ts < h.valid_from or (h.valid_to is not null and f.event_ts >= h.valid_to)
    or h.user_id <> f.user_key)
