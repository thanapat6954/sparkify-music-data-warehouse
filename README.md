# Sparkify Music Streaming Data Warehouse

ระบบคลังข้อมูลเพื่อการวิเคราะห์พฤติกรรมการสตรีมเพลงและการรักษาฐานสมาชิก
Data Warehouse course project · thanapat6954

โปรเจกต์นี้อ่าน Sparkify JSON จาก ZIP ที่ให้มา แล้วสร้างคลังข้อมูลด้วย **Python + dbt** มี **DuckDB** สำหรับรันบนเครื่อง และ **PostgreSQL 16 + Metabase** สำหรับใช้งานตามแนวทางวิชา

## ขอบเขตที่ข้อมูลรองรับจริง

ตรวจจากไฟล์ในเครื่อง: `log_data.zip` มี **8,056 events** และ `song_data.zip` มี **14,896 catalog rows** ข้อมูล events อยู่ในเดือน **พฤศจิกายน 2018 (UTC)** ขนาดและ SHA-256 ดูได้ที่ [Data Profile](reports/data_profile.json)

| คำถาม | ทำได้แค่ไหน |
|---|---|
| ฟังเพลง/ศิลปินใดในแต่ละช่วงเวลา | ทำได้จาก `NextSong`, `song`, `artist`, `ts` |
| ผู้ใช้ฟังเพลงประเภท/Genre ใด | ยังทำไม่ได้ ไม่มี Genre |
| DAU / MAU | ทำได้ โดยนิยาม Active = ผู้ใช้ที่มี `NextSong` |
| Free/Paid มีปริมาณการฟังต่างกันอย่างไร | เปรียบเทียบจำนวนเพลงและผลรวมความยาวเพลง ณ สถานะตอนเกิด event |
| ชั่วโมงที่ผู้ใช้ฟังจริง | ยังวัดไม่ได้ ใช้ **Played track hours** เป็นผลรวม `length` ของ `NextSong` เท่านั้น |
| สมาชิกยกเลิกเมื่อใด / Churn rate | ยังวัดไม่ได้ ไม่มี `Cancellation Confirmation` |
| กดข้าม / Like / Dislike | ไม่มีเหตุการณ์เหล่านี้ในชุดที่ให้มา |
| สัญญาณการใช้งานลดลง | ทำได้แบบกฎคัดกรองที่ยังไม่ผ่านการประเมิน Churn |
| รายได้และประสิทธิภาพโฆษณา | ไม่มีราคา รายได้ หรือ Ad impressions |

`NextSong` ไม่ได้หมายความว่าผู้ใช้กด Skip และ `Upgrade` เป็นการเปิดหน้า ไม่ใช่การอัปเกรดสำเร็จ ใช้ `Submit Upgrade` เป็น **submission event** และประวัติ `level` เป็นสถานะที่สังเกตได้

## รันบนเครื่อง Windows

ใช้ Python **3.11** และวางไฟล์ต้นฉบับไว้ตามนี้ (ZIP ไม่ต้องแตก):

```text
dataset/dataset/log_data.zip
dataset/dataset/song_data.zip
```

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/profile_data.py
.\.venv\Scripts\python.exe scripts/pipeline.py
```

pipeline โหลด raw แบบ deduplicate แล้วรัน `dbt build` ซึ่งสร้าง models และทดสอบ ก่อน export CSV/JSON ไป `reports/` ฐานข้อมูลอยู่ที่ `warehouse/sparkify.duckdb` รันซ้ำได้โดยไม่เพิ่ม events ซ้ำ ใช้ `--data-dir PATH` เพื่อระบุโฟลเดอร์ ZIP อื่นได้

เครื่องที่ clone ใหม่ต้องมี ZIP ต้นฉบับก่อนรันข้อมูลจริง เพราะ repo ไม่เผยแพร่ raw logs ที่ยังไม่ยืนยันสิทธิ์แจกจ่าย รายงานสรุปและ SHA-256 ที่ตรวจสอบแล้วอยู่ใน repo ส่วน CI ใช้ fixture สังเคราะห์ที่สร้างชั่วคราวและไม่ปะปนกับผลจริง

```powershell
# Behavioral regression: duplicate replay, late arrival, membership history
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
# dbt lineage และเอกสาร
$env:SPARKIFY_DUCKDB_PATH = (Join-Path (Get-Location) 'warehouse/sparkify.duckdb')
.\.venv\Scripts\dbt.exe docs generate --project-dir dbt --profiles-dir dbt
.\.venv\Scripts\dbt.exe docs serve --project-dir dbt --profiles-dir dbt --port 28088
```

## รัน PostgreSQL + Metabase

ต้องมี Docker Desktop engine ที่พร้อมใช้งาน:

```powershell
Copy-Item .env.example .env
# แก้ PGPASSWORD ใน .env เป็นรหัสผ่านสำหรับสภาพแวดล้อมนี้
docker compose up -d postgres
docker compose --profile run run --build --rm pipeline
docker compose --profile bi up -d metabase
```

เปิด Metabase ที่ [localhost:23000](http://localhost:23000) แล้วเชื่อม PostgreSQL ด้วย host `postgres`, port `5432`, database/user ตาม `.env` เลือก schema `analytics` ดู SQL และขั้นตอนสร้าง Dashboard ใน [คู่มือ BI](docs/dashboard.md) การเริ่ม Compose ยังไม่ได้สร้าง account หรือ saved dashboard ให้เอง

## โครงสร้าง

```text
scripts/       อ่าน ZIP, โหลด raw, รัน dbt, profile และ export
dbt/           staging / intermediate / marts / reporting + data tests
sql/           SQL สำหรับ Metabase และตัวอย่าง OLAP
docs/          Requirements, KPI, Star Schema, Bus Matrix, Dictionary
reports/       ผลวิเคราะห์จากข้อมูลจริงและหลักฐานการตรวจสอบ
tests/         Regression test ด้วยข้อมูลสังเคราะห์ชั่วคราว
dags/          ตัวอย่าง DAG สำหรับ worker Airflow 3 ที่ติดตั้งไว้แล้ว
compose.yaml   PostgreSQL + pipeline + Metabase
```

## เอกสารสำหรับนำเสนอ

- [Business Context, Subject Area, Business Process และ KPI](docs/requirements.md)
- [Grain, Star Schema, SCD และ Bus Matrix](docs/modeling.md)
- [Data Dictionary](docs/data_dictionary.md)
- [ผลตรวจสไลด์ Canva และเนื้อหาที่ควรปรับ](docs/slide_review.md)
- [SQL และ Dashboard](docs/dashboard.md)
- [ผลจริงและสถานะการทดสอบ](reports/validation.md)

## แนวทางวิชาและแหล่งอ้างอิง

ใช้ [E27-25/dsba8-data-warehouse](https://github.com/E27-25/dsba8-data-warehouse) เป็นแนวทางเรื่อง KPI layer, Star Schema, SCD, Fact Grain, Summary, Incremental และ orchestration โค้ดในโปรเจกต์นี้เขียนสำหรับ Sparkify โดยเฉพาะ ไม่ใช่การ fork แบบฝึกหัด Coffee Sales

แหล่งเทคนิค: [dbt unique key](https://docs.getdbt.com/reference/resource-configs/unique_key), [PostgreSQL incremental strategies](https://docs.getdbt.com/reference/resource-configs/postgres-configs), [dbt-duckdb adapter](https://github.com/duckdb/dbt-duckdb)

แหล่งข้อมูลที่ยืนยันได้ตอนทำงานคือ ZIP ที่เจ้าของโปรเจกต์ให้มา ยังไม่มีหลักฐาน URL ดาวน์โหลดต้นทางและ license ของไฟล์ชุดนี้ จึงไม่อ้างว่าดึงข้อมูลจาก Spotify API หรือดาวน์โหลด Kaggle สำเร็จ
