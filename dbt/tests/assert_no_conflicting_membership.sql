-- Equal timestamps cannot define a strict temporal interval for conflicting levels.
select user_id, event_ts from {{ ref('stg_events') }} where user_id is not null
group by user_id, event_ts having count(distinct membership_level) > 1
