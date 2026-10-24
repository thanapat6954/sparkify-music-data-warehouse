select
    event_id, event_ts, cast(event_ts as date) as event_date,
    user_id, gender, membership_level, location, session_id,
    item_in_session, song, artist, length_seconds, page, auth,
    status, user_agent, device_family, browser_family, source_file,
    case when page = 'NextSong' then 1 else 0 end as is_songplay,
    case when page = 'Submit Upgrade' then 1 else 0 end as is_upgrade_submission,
    case when page = 'Submit Downgrade' then 1 else 0 end as is_downgrade_submission,
    case when page = 'Cancellation Confirmation' then 1 else 0 end as is_cancellation_confirmation
from {{ source('raw', 'events') }}
