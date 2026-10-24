select 'daily' as failure where
    (select sum(songplays) from {{ ref('rpt_daily_kpis') }}) <>
    (select sum(is_songplay) from {{ ref('fact_user_events') }})
union all select 'membership' where
    (select sum(songplays) from {{ ref('rpt_listening_by_membership') }}) <>
    (select sum(is_songplay) from {{ ref('fact_user_events') }})
