# BI Dashboard และ SQL

ไฟล์ [sql/dashboard_queries.sql](../sql/dashboard_queries.sql) ใช้กับ schema `analytics` ได้ทั้ง DuckDB และ PostgreSQL ถ้าใช้ Metabase ตาม Compose ให้เชื่อม PostgreSQL host `postgres`, port `5432` (ไม่ใช่ localhost ภายใน container) โดยใช้ค่ารหัสผ่านจาก `.env`

## Layout สำหรับสร้าง Saved Dashboard

| แถว | Visualization | Source | Filter / หมายเหตุ |
|---|---|---|---|
| 1 | Cards: MAU, Songplays, Played track hours | rpt_monthly_kpis | เดือน UTC; label ชัดเจนว่าเป็น track hours |
| 2 ซ้าย | เส้น DAU ตามวัน | rpt_daily_kpis | date range; วันที่ไม่มี NextSong ควรเติม 0 หากใช้ช่วงนอกข้อมูล |
| 2 ขวา | 100% stacked Free/Paid track hours | rpt_listening_by_membership | แบ่ง subscription_key; normalize ตามวันที่ |
| 3 | Heatmap weekday × hour | rpt_listening_heatmap | ค่า songplays; weekday 1=จันทร์, hour เป็น UTC |
| 4 ซ้าย/ขวา | Top 10 artists / songs | rpt_top_artists, rpt_top_songs | เลือก daypart_utc แล้ว rank<=10 |
| 5 | Engagement watchlist table | rpt_engagement_watchlist | เฉพาะ engagement_decline / inactive_7d พร้อมแสดง cutoff |
| Footer | ข้อจำกัด | ข้อความ | ไม่มี Genre/Skip/Dislike/Churn labels, hours คือความยาวเพลง |

Top content และ heatmap ที่ materialize ตอนนี้ครอบคลุม **ทั้ง dataset** ไม่มี event_date ใน grain จึงใช้ date filter รายวันกับสองตารางนี้ไม่ได้ หากต้องการ date filter ให้ query fact ตามตัวอย่าง SQL แล้ว aggregate หลัง filter ส่วน watchlist เป็น snapshot ณวันสุดท้ายของ dataset ไม่ใช่ live forecast

## ขั้นตอน Metabase

1. เปิด `docker compose --profile bi up -d metabase` และตั้งบัญชีใน local Metabase ด้วยตนเอง
2. Add database: PostgreSQL แล้ว sync schema `analytics`
3. สร้าง SQL question จาก queries เลือก visual ตามตาราง บันทึกลง collection ของโปรเจกต์
4. สร้าง Dashboard และเพิ่ม cards/filters โดยผูก filter เฉพาะ field ที่มีอยู่จริงใน grain นั้น
5. ตรวจยอดรวม Songplays และ track hours กับ `reports/summary.json`

## Saved Dashboard ที่ใช้งานจริง

รัน `python scripts/bootstrap_metabase.py` หลังเปิด PostgreSQL/Metabase แล้ว script จะสร้างหรือ update คำถามและ Dashboard ชื่อเดิม ไม่เพิ่มซ้ำ ทุกคำถามต้อง execute สำเร็จก่อนบันทึกหลักฐานใน `reports/metabase_dashboard.json` บัญชี BI อ่านได้เฉพาะ schema `analytics` ส่วน local admin email/password เก็บใน ignored `.env`

บนเครื่องพัฒนา Dashboard อยู่ที่ [localhost:23000/dashboard/2](http://localhost:23000/dashboard/2) มี KPI cards, DAU line, Free/Paid track hours, hourly songplays, Top 10 artists, screening summary และ submissions รวม 9 คำถาม ตรวจภาพจริงได้ที่ [ภาพ Dashboard](../presentations/assets/metabase-dashboard.png)

Dashboard ใช้ช่วงข้อมูลทั้งเดือน พ.ย. 2018 ยังไม่มี global date filter จึงไม่ควรตีความเป็น live monitoring รายวันนอก sample นี้ ไม่ต้องมี Metabase เพื่อรัน/ทดสอบคลังข้อมูล
