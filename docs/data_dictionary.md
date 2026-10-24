# Data Dictionary

สร้างจากฐานข้อมูลที่ build จริงด้วย `python scripts/generate_dictionary.py` ชนิดข้อมูลแสดงตาม DuckDB (PostgreSQL ใช้ชนิด SQL ที่เทียบกัน เช่น DOUBLE PRECISION/TIMESTAMP WITHOUT TIME ZONE)

Nullability ใน CTAS/view อาจไม่บังคับด้วย DDL: ใช้ dbt not_null/unique/relationships และ singular tests เป็นสัญญาคุณภาพ ดู dbt/models/schema.yml และ dbt/tests/

Raw logs มี 18 fields เดิม แต่ loader ไม่เก็บ firstName, lastName, registration, method ที่ไม่จำเป็นต่อ KPI และเพิ่ม canonical event key, parsed timestamp, device classification และ source lineage

## analytics.dim_artist

| Column | SQL Type | นิยาม |
|---|---|---|
| artist_key | VARCHAR | MD5 ของชื่อศิลปิน หรือ unknown |
| artist_name | VARCHAR | ชื่อศิลปินตาม source |
## analytics.dim_device

| Column | SQL Type | นิยาม |
|---|---|---|
| device_key | VARCHAR | MD5(userAgent หรือ unknown) |
| user_agent | VARCHAR | สตริง userAgent ดิบ; null ได้ |
| device_family | VARCHAR | ประเภทอุปกรณ์จาก token ใน userAgent อย่างหยาบ |
| browser_family | VARCHAR | ประเภท browser จาก token ใน userAgent อย่างหยาบ |
## analytics.dim_interaction

| Column | SQL Type | นิยาม |
|---|---|---|
| interaction_key | VARCHAR | FK ไป dim_interaction ใช้ page เป็น key |
| page | VARCHAR | ชนิด event ตาม source เช่น NextSong, Upgrade, Submit Upgrade |
| interaction_group | VARCHAR | กลุ่มที่กำหนดจาก page: streaming/subscription/error/navigation |
## analytics.dim_location

| Column | SQL Type | นิยาม |
|---|---|---|
| location_key | VARCHAR | MD5(location หรือ unknown) |
| location | VARCHAR | สตริงพื้นที่จาก source หรือ unknown; ไม่ใช่พิกัด |
## analytics.dim_song

| Column | SQL Type | นิยาม |
|---|---|---|
| song_key | VARCHAR | MD5(artist + chr(31) + song) หรือ unknown |
| song_title | VARCHAR | ชื่อเพลงจาก log |
| artist_name | VARCHAR | ชื่อศิลปินตาม source |
| artist_key | VARCHAR | MD5 ของชื่อศิลปิน หรือ unknown |
| catalog_song_id | VARCHAR | song_id เฉพาะ exact unique match ของ title+artist |
| release_year | INTEGER | ปีจาก catalog เมื่อ match เดียว; 0 แปลงเป็น null |
| catalog_duration_seconds | DOUBLE | duration จาก catalog เมื่อ match เดียว |
| catalog_match_status | VARCHAR | exact_unique / ambiguous / unmatched / not_applicable |
## analytics.dim_subscription

| Column | SQL Type | นิยาม |
|---|---|---|
| subscription_key | VARCHAR | FK ไป dim_subscription ระดับ ณ event |
| membership_level | VARCHAR | ระดับที่สังเกตใน event เช่น free/paid |
## analytics.dim_time

| Column | SQL Type | นิยาม |
|---|---|---|
| time_key | TIMESTAMP | FK ไป dim_time ใช้ timestamp UTC ไม่ปัดเศษ |
| event_date | DATE | วันที่ UTC ของ event / snapshot |
| year | INTEGER | ปีใน source / มิติ calendar |
| month | INTEGER | เลขเดือนใน dim_time หรือวันแรกของเดือนใน monthly summary |
| iso_week | INTEGER | เลขสัปดาห์ ISO |
| iso_year | INTEGER | ปี ISO week |
| iso_weekday | INTEGER | วัน ISO 1=จันทร์ ถึง 7=อาทิตย์ |
| hour_utc | INTEGER | ชั่วโมง UTC 0–23 |
| is_weekend | BOOLEAN | เสาร์หรืออาทิตย์ ไม่ใช่วันหยุดราชการ |
| daypart_utc | VARCHAR | night<6, morning<12, afternoon<18, evening>=18 |
## analytics.dim_user

| Column | SQL Type | นิยาม |
|---|---|---|
| user_key | VARCHAR | userId หรือ unknown; ไม่เก็บ firstName/lastName |
| gender | VARCHAR | เพศตาม source; ไม่อนุมานค่าที่ไม่มี |
| latest_location | VARCHAR | location ที่ event ล่าสุดระบุ (Type 1) |
| first_seen | TIMESTAMP | เวลา event แรกของ account ในข้อมูลที่โหลด |
## analytics.dim_user_subscription

| Column | SQL Type | นิยาม |
|---|---|---|
| subscription_history_key | VARCHAR | MD5(userId:valid_from) สำหรับ membership interval หรือ unknown |
| user_id | VARCHAR | Natural account ID; null สำหรับ anonymous |
| membership_level | VARCHAR | ระดับที่สังเกตใน event เช่น free/paid |
| valid_from | TIMESTAMP | เวลาเริ่มช่วงที่สังเกตได้ รวม timestamp นี้ |
| valid_to | TIMESTAMP | เวลาสิ้นสุดช่วง ไม่รวม timestamp นี้; null คือช่วงสุดท้ายที่สังเกตได้ |
| is_current | BOOLEAN | ช่วงล่าสุดในข้อมูล ไม่รับประกันสถานะปัจจุบันนอก sample |
## analytics.fact_user_day

| Column | SQL Type | นิยาม |
|---|---|---|
| user_key | VARCHAR | userId หรือ unknown; ไม่เก็บ firstName/lastName |
| event_date | DATE | วันที่ UTC ของ event / snapshot |
| events | BIGINT | จำนวน events ใน grain ของตาราง |
| songplays | HUGEINT | จำนวน NextSong ใน grain ของตาราง |
| sessions | BIGINT | distinct session_id ต่อ user/date; ไม่ additive ข้ามวัน |
| played_track_duration_seconds | DOUBLE | length เฉพาะ NextSong; event อื่น = 0 |
| upgrade_submissions | HUGEINT | จำนวน Submit Upgrade events |
| downgrade_submissions | HUGEINT | จำนวน Submit Downgrade events |
## analytics.fact_user_events

| Column | SQL Type | นิยาม |
|---|---|---|
| event_id | VARCHAR | SHA-256 ของ canonical JSON เป็น event key ภายใต้สมมติฐาน content dedup |
| time_key | TIMESTAMP | FK ไป dim_time ใช้ timestamp UTC ไม่ปัดเศษ |
| event_ts | TIMESTAMP | เวลาเกิด event, timestamp UTC |
| event_date | DATE | วันที่ UTC ของ event / snapshot |
| user_key | VARCHAR | userId หรือ unknown; ไม่เก็บ firstName/lastName |
| subscription_history_key | VARCHAR | MD5(userId:valid_from) สำหรับ membership interval หรือ unknown |
| subscription_key | VARCHAR | FK ไป dim_subscription ระดับ ณ event |
| song_key | VARCHAR | MD5(artist + chr(31) + song) หรือ unknown |
| artist_key | VARCHAR | MD5 ของชื่อศิลปิน หรือ unknown |
| device_key | VARCHAR | MD5(userAgent หรือ unknown) |
| location_key | VARCHAR | MD5(location หรือ unknown) |
| interaction_key | VARCHAR | FK ไป dim_interaction ใช้ page เป็น key |
| session_id | BIGINT | sessionId ตาม source; ถ้าต้องการ unique session ให้ใช้ร่วมกับ user/session context |
| item_in_session | INTEGER | ลำดับ event ตาม source; ใช้ประกอบการตรวจ ไม่ใช่ event PK |
| event_count | INTEGER | 1 ต่อ event, additive |
| is_songplay | INTEGER | 1 เมื่อ page=NextSong; อื่นๆ=0 |
| is_upgrade_submission | INTEGER | 1 เมื่อ page=Submit Upgrade ไม่รับประกัน payment success |
| is_downgrade_submission | INTEGER | 1 เมื่อ page=Submit Downgrade ไม่ใช่ Churn |
| is_cancellation_confirmation | INTEGER | 1 เมื่อมี Cancellation Confirmation; ชุดนี้ไม่มี event ชนิดนี้ จึงไม่ใช้เป็น label ฝึกโมเดล |
| played_track_duration_seconds | DOUBLE | length เฉพาะ NextSong; event อื่น = 0 |
| status | INTEGER | HTTP status จาก source |
| source_file | VARCHAR | ชื่อสมาชิกใน ZIP:เลขบรรทัด เพื่อย้อนกลับไปตรวจ source |
## analytics.int_subscription_history

| Column | SQL Type | นิยาม |
|---|---|---|
| subscription_history_key | VARCHAR | MD5(userId:valid_from) สำหรับ membership interval หรือ unknown |
| user_id | VARCHAR | Natural account ID; null สำหรับ anonymous |
| membership_level | VARCHAR | ระดับที่สังเกตใน event เช่น free/paid |
| valid_from | TIMESTAMP | เวลาเริ่มช่วงที่สังเกตได้ รวม timestamp นี้ |
| valid_to | TIMESTAMP | เวลาสิ้นสุดช่วง ไม่รวม timestamp นี้; null คือช่วงสุดท้ายที่สังเกตได้ |
| is_current | BOOLEAN | ช่วงล่าสุดในข้อมูล ไม่รับประกันสถานะปัจจุบันนอก sample |
## analytics.rpt_daily_kpis

| Column | SQL Type | นิยาม |
|---|---|---|
| event_date | DATE | วันที่ UTC ของ event / snapshot |
| events | BIGINT | จำนวน events ใน grain ของตาราง |
| songplays | HUGEINT | จำนวน NextSong ใน grain ของตาราง |
| dau | BIGINT | distinct identified users ที่มี NextSong ต่อวัน UTC |
| played_track_hours | DOUBLE | ผลรวม played_track_duration_seconds / 3600 |
| upgrade_submissions | HUGEINT | จำนวน Submit Upgrade events |
| downgrade_submissions | HUGEINT | จำนวน Submit Downgrade events |
## analytics.rpt_engagement_watchlist

| Column | SQL Type | นิยาม |
|---|---|---|
| user_key | VARCHAR | userId หรือ unknown; ไม่เก็บ firstName/lastName |
| as_of_date | DATE | วันล่าสุดของ events ในข้อมูลที่โหลด |
| observed_days | BIGINT | as_of_date - first_seen date + 1 |
| current_7d_songplays | HUGEINT | จำนวนเพลงช่วง cutoff-6 ถึง cutoff รวมปลายทั้งสอง |
| prior_7d_songplays | HUGEINT | จำนวนเพลงช่วง cutoff-13 ถึง cutoff-7 รวมปลายทั้งสอง |
| days_since_last_songplay | BIGINT | จำนวนวันระหว่าง cutoff กับ NextSong ล่าสุด; null ถ้าไม่เคยฟัง |
| songplay_decline_fraction | DOUBLE | 1-current/prior เมื่อ history>=14 และ prior>=5; null กรณีข้อมูลไม่พอ |
| watchlist_reason | VARCHAR | insufficient_history / engagement_decline / inactive_7d / no_rule_trigger |
| interpretation | VARCHAR | unvalidated_engagement_rule: ไม่ใช่ churn prediction |
## analytics.rpt_listening_by_membership

| Column | SQL Type | นิยาม |
|---|---|---|
| event_date | DATE | วันที่ UTC ของ event / snapshot |
| subscription_key | VARCHAR | FK ไป dim_subscription ระดับ ณ event |
| songplays | HUGEINT | จำนวน NextSong ใน grain ของตาราง |
| played_track_hours | DOUBLE | ผลรวม played_track_duration_seconds / 3600 |
## analytics.rpt_listening_heatmap

| Column | SQL Type | นิยาม |
|---|---|---|
| iso_weekday | INTEGER | วัน ISO 1=จันทร์ ถึง 7=อาทิตย์ |
| hour_utc | INTEGER | ชั่วโมง UTC 0–23 |
| daypart_utc | VARCHAR | night<6, morning<12, afternoon<18, evening>=18 |
| songplays | BIGINT | จำนวน NextSong ใน grain ของตาราง |
| played_track_hours | DOUBLE | ผลรวม played_track_duration_seconds / 3600 |
## analytics.rpt_monthly_kpis

| Column | SQL Type | นิยาม |
|---|---|---|
| month | DATE | เลขเดือนใน dim_time หรือวันแรกของเดือนใน monthly summary |
| mau | BIGINT | distinct identified users ที่มี NextSong ต่อเดือน UTC |
| songplays | HUGEINT | จำนวน NextSong ใน grain ของตาราง |
| played_track_hours | DOUBLE | ผลรวม played_track_duration_seconds / 3600 |
## analytics.rpt_top_artists

| Column | SQL Type | นิยาม |
|---|---|---|
| daypart_utc | VARCHAR | night<6, morning<12, afternoon<18, evening>=18 |
| artist_name | VARCHAR | ชื่อศิลปินตาม source |
| songplays | BIGINT | จำนวน NextSong ใน grain ของตาราง |
| artist_rank | BIGINT | อันดับในแต่ละ daypart ใช้ชื่อเรียงกรณีจำนวนเท่ากัน |
## analytics.rpt_top_songs

| Column | SQL Type | นิยาม |
|---|---|---|
| daypart_utc | VARCHAR | night<6, morning<12, afternoon<18, evening>=18 |
| song_title | VARCHAR | ชื่อเพลงจาก log |
| artist_name | VARCHAR | ชื่อศิลปินตาม source |
| songplays | BIGINT | จำนวน NextSong ใน grain ของตาราง |
| song_rank | BIGINT | อันดับในแต่ละ daypart ใช้ชื่อเรียงกรณีจำนวนเท่ากัน |
## analytics.stg_events

| Column | SQL Type | นิยาม |
|---|---|---|
| event_id | VARCHAR | SHA-256 ของ canonical JSON เป็น event key ภายใต้สมมติฐาน content dedup |
| event_ts | TIMESTAMP | เวลาเกิด event, timestamp UTC |
| event_date | DATE | วันที่ UTC ของ event / snapshot |
| user_id | VARCHAR | Natural account ID; null สำหรับ anonymous |
| gender | VARCHAR | เพศตาม source; ไม่อนุมานค่าที่ไม่มี |
| membership_level | VARCHAR | ระดับที่สังเกตใน event เช่น free/paid |
| location | VARCHAR | สตริงพื้นที่จาก source หรือ unknown; ไม่ใช่พิกัด |
| session_id | BIGINT | sessionId ตาม source; ถ้าต้องการ unique session ให้ใช้ร่วมกับ user/session context |
| item_in_session | INTEGER | ลำดับ event ตาม source; ใช้ประกอบการตรวจ ไม่ใช่ event PK |
| song | VARCHAR | ชื่อเพลงใน event |
| artist | VARCHAR | ชื่อศิลปินใน event |
| length_seconds | DOUBLE | ความยาวเพลงใน source; ไม่ใช่เวลาที่ฟังจริง |
| page | VARCHAR | ชนิด event ตาม source เช่น NextSong, Upgrade, Submit Upgrade |
| auth | VARCHAR | สถานะการเข้าสู่ระบบตาม source |
| status | INTEGER | HTTP status จาก source |
| user_agent | VARCHAR | สตริง userAgent ดิบ; null ได้ |
| device_family | VARCHAR | ประเภทอุปกรณ์จาก token ใน userAgent อย่างหยาบ |
| browser_family | VARCHAR | ประเภท browser จาก token ใน userAgent อย่างหยาบ |
| source_file | VARCHAR | ชื่อสมาชิกใน ZIP:เลขบรรทัด เพื่อย้อนกลับไปตรวจ source |
| is_songplay | INTEGER | 1 เมื่อ page=NextSong; อื่นๆ=0 |
| is_upgrade_submission | INTEGER | 1 เมื่อ page=Submit Upgrade ไม่รับประกัน payment success |
| is_downgrade_submission | INTEGER | 1 เมื่อ page=Submit Downgrade ไม่ใช่ Churn |
| is_cancellation_confirmation | INTEGER | 1 เมื่อมี Cancellation Confirmation; ชุดนี้ไม่มี event ชนิดนี้ จึงไม่ใช้เป็น label ฝึกโมเดล |
## analytics.stg_songs

| Column | SQL Type | นิยาม |
|---|---|---|
| song_id | VARCHAR | Native ID ใน song catalog ไม่มีใน event logs |
| artist_id | VARCHAR | Native artist ID ใน song catalog |
| title | VARCHAR | ชื่อเพลงใน catalog |
| artist_name | VARCHAR | ชื่อศิลปินตาม source |
| duration | DOUBLE | ความยาวเพลงใน catalog หน่วยวินาที |
| year | INTEGER | ปีใน source / มิติ calendar |
| artist_location | VARCHAR | พื้นที่ศิลปินใน catalog; null ได้ |
## raw.events

| Column | SQL Type | นิยาม |
|---|---|---|
| event_id | VARCHAR | SHA-256 ของ canonical JSON เป็น event key ภายใต้สมมติฐาน content dedup |
| event_ts | TIMESTAMP | เวลาเกิด event, timestamp UTC |
| user_id | VARCHAR | Natural account ID; null สำหรับ anonymous |
| gender | VARCHAR | เพศตาม source; ไม่อนุมานค่าที่ไม่มี |
| membership_level | VARCHAR | ระดับที่สังเกตใน event เช่น free/paid |
| location | VARCHAR | สตริงพื้นที่จาก source หรือ unknown; ไม่ใช่พิกัด |
| session_id | BIGINT | sessionId ตาม source; ถ้าต้องการ unique session ให้ใช้ร่วมกับ user/session context |
| item_in_session | INTEGER | ลำดับ event ตาม source; ใช้ประกอบการตรวจ ไม่ใช่ event PK |
| song | VARCHAR | ชื่อเพลงใน event |
| artist | VARCHAR | ชื่อศิลปินใน event |
| length_seconds | DOUBLE | ความยาวเพลงใน source; ไม่ใช่เวลาที่ฟังจริง |
| page | VARCHAR | ชนิด event ตาม source เช่น NextSong, Upgrade, Submit Upgrade |
| auth | VARCHAR | สถานะการเข้าสู่ระบบตาม source |
| status | INTEGER | HTTP status จาก source |
| user_agent | VARCHAR | สตริง userAgent ดิบ; null ได้ |
| device_family | VARCHAR | ประเภทอุปกรณ์จาก token ใน userAgent อย่างหยาบ |
| browser_family | VARCHAR | ประเภท browser จาก token ใน userAgent อย่างหยาบ |
| source_file | VARCHAR | ชื่อสมาชิกใน ZIP:เลขบรรทัด เพื่อย้อนกลับไปตรวจ source |
## raw.songs

| Column | SQL Type | นิยาม |
|---|---|---|
| song_id | VARCHAR | Native ID ใน song catalog ไม่มีใน event logs |
| artist_id | VARCHAR | Native artist ID ใน song catalog |
| title | VARCHAR | ชื่อเพลงใน catalog |
| artist_name | VARCHAR | ชื่อศิลปินตาม source |
| duration | DOUBLE | ความยาวเพลงใน catalog หน่วยวินาที |
| year | INTEGER | ปีใน source / มิติ calendar |
| artist_location | VARCHAR | พื้นที่ศิลปินใน catalog; null ได้ |
