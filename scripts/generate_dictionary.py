"""Generate every raw/warehouse column and SQL type from the built database."""
import argparse
from pathlib import Path
from pipeline import ROOT, connect, query

MEANINGS = {
    'event_id': 'SHA-256 ของ canonical JSON เป็น event key ภายใต้สมมติฐาน content dedup',
    'event_ts': 'เวลาเกิด event, timestamp UTC',
    'event_date': 'วันที่ UTC ของ event / snapshot',
    'time_key': 'FK ไป dim_time ใช้ timestamp UTC ไม่ปัดเศษ',
    'user_id': 'Natural account ID; null สำหรับ anonymous',
    'user_key': 'userId หรือ unknown; ไม่เก็บ firstName/lastName',
    'gender': 'เพศตาม source; ไม่อนุมานค่าที่ไม่มี',
    'membership_level': 'ระดับที่สังเกตใน event เช่น free/paid',
    'subscription_key': 'FK ไป dim_subscription ระดับ ณ event',
    'subscription_history_key': 'MD5(userId:valid_from) สำหรับ membership interval หรือ unknown',
    'valid_from': 'เวลาเริ่มช่วงที่สังเกตได้ รวม timestamp นี้',
    'valid_to': 'เวลาสิ้นสุดช่วง ไม่รวม timestamp นี้; null คือช่วงสุดท้ายที่สังเกตได้',
    'is_current': 'ช่วงล่าสุดในข้อมูล ไม่รับประกันสถานะปัจจุบันนอก sample',
    'first_seen': 'เวลา event แรกของ account ในข้อมูลที่โหลด',
    'latest_location': 'location ที่ event ล่าสุดระบุ (Type 1)',
    'location': 'สตริงพื้นที่จาก source หรือ unknown; ไม่ใช่พิกัด',
    'location_key': 'MD5(location หรือ unknown)',
    'session_id': 'sessionId ตาม source; ถ้าต้องการ unique session ให้ใช้ร่วมกับ user/session context',
    'item_in_session': 'ลำดับ event ตาม source; ใช้ประกอบการตรวจ ไม่ใช่ event PK',
    'song': 'ชื่อเพลงใน event', 'song_title': 'ชื่อเพลงจาก log',
    'song_key': 'MD5(artist + chr(31) + song) หรือ unknown',
    'artist': 'ชื่อศิลปินใน event', 'artist_name': 'ชื่อศิลปินตาม source',
    'artist_key': 'MD5 ของชื่อศิลปิน หรือ unknown',
    'length_seconds': 'ความยาวเพลงใน source; ไม่ใช่เวลาที่ฟังจริง',
    'played_track_duration_seconds': 'length เฉพาะ NextSong; event อื่น = 0',
    'played_track_hours': 'ผลรวม played_track_duration_seconds / 3600',
    'page': 'ชนิด event ตาม source เช่น NextSong, Upgrade, Submit Upgrade',
    'interaction_key': 'FK ไป dim_interaction ใช้ page เป็น key',
    'interaction_group': 'กลุ่มที่กำหนดจาก page: streaming/subscription/error/navigation',
    'auth': 'สถานะการเข้าสู่ระบบตาม source', 'status': 'HTTP status จาก source',
    'user_agent': 'สตริง userAgent ดิบ; null ได้',
    'device_key': 'MD5(userAgent หรือ unknown)',
    'device_family': 'ประเภทอุปกรณ์จาก token ใน userAgent อย่างหยาบ',
    'browser_family': 'ประเภท browser จาก token ใน userAgent อย่างหยาบ',
    'source_file': 'ชื่อสมาชิกใน ZIP:เลขบรรทัด เพื่อย้อนกลับไปตรวจ source',
    'event_count': '1 ต่อ event, additive', 'is_songplay': '1 เมื่อ page=NextSong; อื่นๆ=0',
    'is_upgrade_submission': '1 เมื่อ page=Submit Upgrade ไม่รับประกัน payment success',
    'is_downgrade_submission': '1 เมื่อ page=Submit Downgrade ไม่ใช่ Churn',
    'is_cancellation_confirmation': '1 เมื่อมี Cancellation Confirmation; ชุดนี้ไม่มี event ชนิดนี้ จึงไม่ใช้เป็น label ฝึกโมเดล',
    'song_id': 'Native ID ใน song catalog ไม่มีใน event logs',
    'artist_id': 'Native artist ID ใน song catalog', 'title': 'ชื่อเพลงใน catalog',
    'duration': 'ความยาวเพลงใน catalog หน่วยวินาที', 'year': 'ปีใน source / มิติ calendar',
    'artist_location': 'พื้นที่ศิลปินใน catalog; null ได้',
    'catalog_song_id': 'song_id เฉพาะ exact unique match ของ title+artist',
    'release_year': 'ปีจาก catalog เมื่อ match เดียว; 0 แปลงเป็น null',
    'catalog_duration_seconds': 'duration จาก catalog เมื่อ match เดียว',
    'catalog_match_status': 'exact_unique / ambiguous / unmatched / not_applicable',
    'month': 'เลขเดือนใน dim_time หรือวันแรกของเดือนใน monthly summary',
    'iso_week': 'เลขสัปดาห์ ISO', 'iso_year': 'ปี ISO week',
    'iso_weekday': 'วัน ISO 1=จันทร์ ถึง 7=อาทิตย์', 'hour_utc': 'ชั่วโมง UTC 0–23',
    'is_weekend': 'เสาร์หรืออาทิตย์ ไม่ใช่วันหยุดราชการ',
    'daypart_utc': 'night<6, morning<12, afternoon<18, evening>=18',
    'events': 'จำนวน events ใน grain ของตาราง', 'songplays': 'จำนวน NextSong ใน grain ของตาราง',
    'sessions': 'distinct session_id ต่อ user/date; ไม่ additive ข้ามวัน',
    'upgrade_submissions': 'จำนวน Submit Upgrade events', 'downgrade_submissions': 'จำนวน Submit Downgrade events',
    'dau': 'distinct identified users ที่มี NextSong ต่อวัน UTC',
    'mau': 'distinct identified users ที่มี NextSong ต่อเดือน UTC',
    'artist_rank': 'อันดับในแต่ละ daypart ใช้ชื่อเรียงกรณีจำนวนเท่ากัน',
    'song_rank': 'อันดับในแต่ละ daypart ใช้ชื่อเรียงกรณีจำนวนเท่ากัน',
    'as_of_date': 'วันล่าสุดของ events ในข้อมูลที่โหลด',
    'observed_days': 'as_of_date - first_seen date + 1',
    'current_7d_songplays': 'จำนวนเพลงช่วง cutoff-6 ถึง cutoff รวมปลายทั้งสอง',
    'prior_7d_songplays': 'จำนวนเพลงช่วง cutoff-13 ถึง cutoff-7 รวมปลายทั้งสอง',
    'days_since_last_songplay': 'จำนวนวันระหว่าง cutoff กับ NextSong ล่าสุด; null ถ้าไม่เคยฟัง',
    'songplay_decline_fraction': '1-current/prior เมื่อ history>=14 และ prior>=5; null กรณีข้อมูลไม่พอ',
    'watchlist_reason': 'insufficient_history / engagement_decline / inactive_7d / no_rule_trigger',
    'interpretation': 'unvalidated_engagement_rule: ไม่ใช่ churn prediction',
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', choices=['duckdb','postgres'], default='duckdb')
    parser.add_argument('--db-path', type=Path, default=ROOT / 'warehouse' / 'sparkify.duckdb')
    args = parser.parse_args()
    con = connect(args.target, args.db_path)
    try:
        rows = query(con, "select table_schema, table_name, column_name, data_type from information_schema.columns where table_schema in ('raw','analytics') order by table_schema,table_name,ordinal_position")
    finally:
        con.close()
    lines = ['# Data Dictionary', '', 'สร้างจากฐานข้อมูลที่ build จริงด้วย `python scripts/generate_dictionary.py` ชนิดข้อมูลแสดงตาม DuckDB (PostgreSQL ใช้ชนิด SQL ที่เทียบกัน เช่น DOUBLE PRECISION/TIMESTAMP WITHOUT TIME ZONE)', '', 'Nullability ใน CTAS/view อาจไม่บังคับด้วย DDL: ใช้ dbt not_null/unique/relationships และ singular tests เป็นสัญญาคุณภาพ ดู dbt/models/schema.yml และ dbt/tests/', '', 'Raw logs มี 18 fields เดิม แต่ loader ไม่เก็บ firstName, lastName, registration, method ที่ไม่จำเป็นต่อ KPI และเพิ่ม canonical event key, parsed timestamp, device classification และ source lineage', '']
    previous = None
    for r in rows:
        table = r['table_schema'] + '.' + r['table_name']
        if table != previous:
            lines.extend(['## ' + table, '', '| Column | SQL Type | นิยาม |', '|---|---|---|'])
            previous = table
        meaning = MEANINGS.get(r['column_name'])
        if meaning is None:
            raise ValueError('Missing definition: ' + r['column_name'])
        lines.append(f"| {r['column_name']} | {r['data_type']} | {meaning} |")
    (ROOT / 'docs' / 'data_dictionary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
