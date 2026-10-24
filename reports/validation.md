# ผลการตรวจสอบ

วันที่ตรวจ: **25 ตุลาคม 2026 (Asia/Bangkok)**

## ข้อมูลจริง

| รายการ | ผล |
|---|---:|
| Raw events / event fact | 8,056 |
| Song catalog rows | 14,896 |
| ผู้ใช้ที่ระบุ ID ได้จากทุก event | 97 |
| MAU ที่มี NextSong ใน พ.ย. 2018 | 96 |
| Songplays | 6,820 |
| Played track hours | 467.988819 |
| Free songplays / track hours | 1,229 / 85.811817 |
| Paid songplays / track hours | 5,591 / 382.177001 |
| Exact unique catalog matched plays | 333 (ประมาณ 4.88%) |
| Unmatched catalog plays | 6,487 |
| Submit Upgrade / Submit Downgrade | 8 / 1 events |

เวลาที่สังเกต: **2018-11-01 20:57:10.796 UTC ถึง 2018-11-30 19:54:24.796 UTC** วันแรกและวันสุดท้ายไม่ครบ 24 ชั่วโมง ผลลัพธ์นี้มาจาก sample ไม่ใช่ Spotify production

Watchlist ณวันที่ 30 พ.ย. 2018: engagement_decline 18 accounts, inactive_7d 19 accounts, insufficient_history 9 accounts, no_rule_trigger 51 accounts ตัวเลขนี้ **ไม่ใช่จำนวนผู้ยกเลิกสมาชิก** หรือความน่าจะเป็น Churn

## ผลตรวจบนเครื่อง

- `dbt build` ข้อมูลจริง: **21 models สำเร็จ, 47 data tests ผ่าน, 0 failed / warn / skipped** ดู [dbt_build_evidence.json](dbt_build_evidence.json)
- สร้างฐานใหม่จาก ZIP ด้วย loader ปัจจุบัน: โหลดใหม่ 8,056 events และ 14,896 songs, build/test ผ่านเท่ากัน ดู [fresh_build_evidence.json](fresh_build_evidence.json)
- เทียบฐานใหม่กับฐานหลัก: raw counts, songplays และ track hours ตรงกัน
- Replay ZIP เดิม: inserted_events=0, inserted_songs=0 โดยยอด fact ไม่เปลี่ยน
- `python -m unittest discover -s tests -v`: **2 tests ผ่าน** ครอบคลุม stable hash, device parsing, duplicate replay, วันที่ไม่มี activity เป็น 0, late arrival, Free→Paid→Free history และ fact ที่ผูกกับช่วงสมาชิกถูกต้อง
- Query ตัวอย่าง Dashboard **8 statements** และ OLAP **3 statements** รันผ่าน DuckDB จริง
- `pip check`: ผ่าน
- `dbt docs generate`: ผ่าน สร้าง catalog/manifest สำหรับเปิดดูเอกสารและ lineage
- `docker compose config --quiet`: ผ่าน (ตรวจ configuration โดยไม่ต้องเชื่อม engine)

## สถานะส่วนที่ต้องใช้ environment เพิ่ม

- PostgreSQL: มี loader, dbt profile และ Compose; Docker engine บนเครื่องไม่ตอบภายใน timeout จึงยังไม่ได้รันข้อมูลจริงบน local PostgreSQL
- GitHub Actions: **ผ่านทั้ง DuckDB และ PostgreSQL 16** สำหรับ synthetic regression ดู [run 40140579088](https://github.com/thanapat6954/sparkify-music-data-warehouse/actions/runs/40140579088) ซึ่งตรวจโค้ด commit `e0d441a` ครอบคลุม 2 behavioral tests ที่ภายในรัน dbt build/test ก่อนและหลัง late arrival; ผลนี้แยกจากการรันข้อมูลจริงบน DuckDB ข้างต้น
- Metabase: มี Compose, SQL, grain/filter mapping และขั้นตอนสร้าง Dashboard ยังไม่ได้สร้าง saved dashboard หรือ account
- Airflow 3: มี DAG template สำหรับ worker ที่ติดตั้ง dependencies และ mount dataset แล้ว ยังไม่ได้ deploy หรือ trigger DAG บนเครื่องนี้
- Churn model: ยังไม่ได้ฝึกหรือประเมิน เพราะไม่มี label ยืนยันการยกเลิก

## วิธีสร้างผลใหม่

ทำตาม README โดยวาง ZIP ต้นฉบับก่อน แล้วรัน `python scripts/profile_data.py` และ `python scripts/pipeline.py` รายงานที่ commit ไม่ได้รวม raw archive, names, tokens, passwords หรือไฟล์ฐานข้อมูล
