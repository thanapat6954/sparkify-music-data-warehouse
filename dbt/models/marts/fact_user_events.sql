{{ config(materialized='incremental', unique_key='event_id', incremental_strategy='delete+insert') }}
-- Revisit all staged keys on each run, so late events can re-key historical SCD joins.
select e.event_id, e.event_ts as time_key, e.event_ts, e.event_date,
    coalesce(e.user_id, 'unknown') as user_key,
    coalesce(h.subscription_history_key, 'unknown') as subscription_history_key,
    e.membership_level as subscription_key,
    case when e.song is not null and e.artist is not null then md5(e.artist || chr(31) || e.song) else 'unknown' end as song_key,
    coalesce(md5(e.artist), 'unknown') as artist_key,
    md5(coalesce(e.user_agent, 'unknown')) as device_key,
    md5(coalesce(e.location, 'unknown')) as location_key,
    e.page as interaction_key, e.session_id, e.item_in_session,
    1 as event_count, e.is_songplay, e.is_upgrade_submission, e.is_downgrade_submission,
    e.is_cancellation_confirmation,
    case when e.is_songplay = 1 then e.length_seconds else 0 end as played_track_duration_seconds,
    e.status, e.source_file
from {{ ref('stg_events') }} e
left join {{ ref('dim_user_subscription') }} h on e.user_id = h.user_id
    and e.event_ts >= h.valid_from and (e.event_ts < h.valid_to or h.valid_to is null)
