# Business Requirements และ KPI

## หัวข้อ

**ระบบคลังข้อมูลเพื่อการวิเคราะห์พฤติกรรมการสตรีมเพลงและการรักษาฐานสมาชิก**
Music Streaming Behavior & Subscription Churn Analytics Data Warehouse

## Business Context

แพลตฟอร์มเพลงแบบ Freemium มีผู้ใช้ฟรีและผู้จ่ายค่าสมาชิก ทีมคอนเทนต์ต้องเข้าใจว่าเพลงและศิลปินใดได้รับความนิยมในช่วงใด ส่วนทีมสมาชิกต้องสังเกตความเปลี่ยนแปลงของการใช้งาน เพื่อตรวจสอบและออกแบบกิจกรรมรักษาสมาชิก

คลังข้อมูลรวบรวม events ให้เป็นมิติที่ใช้งานร่วมกัน ลดการเตรียม JSON ซ้ำ และกำหนดนิยามตัวชี้วัดให้ตรงกันก่อนนำเข้า BI ข้อมูลชุดนี้ไม่ได้มีรายได้ ต้นทุนหาลูกค้า หรือผลตอบรับแคมเปญ จึงไม่สามารถสรุป ROI หรือยืนยันว่าการฟังน้อยลงเป็นสาเหตุของการยกเลิกได้

## Subject Area และ Business Process

| Subject Area | Business Process | การตัดสินใจ | Fact / รายงาน |
|---|---|---|---|
| User Engagement | ติดตามกิจกรรมและ session | วางแผนช่วงเวลาใช้งาน | fact_user_events, rpt_daily_kpis |
| Music Consumption | ติดตามการเล่นเพลง | จัดลำดับคอนเทนต์และเพลย์ลิสต์ | fact_user_events, rpt_top_songs/artists |
| Subscription | ติดตามระดับสมาชิกและ submissions | ดูการใช้งาน Free/Paid และการเปลี่ยนระดับที่พบ | dim_user_subscription, rpt_listening_by_membership |
| Retention Monitoring | ติดตามปริมาณการใช้งานรายวัน | คัดรายการไปตรวจสอบพฤติกรรมเพิ่มเติม | fact_user_day, rpt_engagement_watchlist |
| Customer Churn (ส่วนต่อยอด) | ยืนยันการยกเลิกและประเมินสัญญาณล่วงหน้า | ทดลองกลยุทธ์รักษาสมาชิก | ยังไม่มี label และ outcome |

## KPI Contract

ทุกช่วงเวลาเป็น UTC เพราะไม่มีเขตเวลาของผู้ใช้ที่ยืนยันได้ การแบ่งเช้า/บ่ายจึงเป็นช่วง UTC ไม่ใช่การอนุมานว่าผู้ใช้กำลังเดินทางหรือทำงาน

| KPI | สูตร / denominator | Grain | เงื่อนไข |
|---|---|---|---|
| DAU | count distinct user_key ที่มี NextSong ในวันนั้น | 1 วัน UTC | ไม่นับ anonymous |
| MAU | count distinct user_key ที่มี NextSong ในเดือนนั้น | 1 เดือน UTC | ไม่ใช่ผลรวม DAU |
| DAU/MAU stickiness (optional) | DAU หาร MAU เดือนเดียวกัน | วัน | เปรียบเทียบภายในเดือนที่สังเกตได้ |
| Songplays | จำนวน events ที่ page = NextSong | event / มิติที่เลือก | ไม่ใช่จำนวนเพลงที่เล่นจบ |
| Played track hours | sum(length ของ NextSong)/3600 | event / วันที่ / ระดับสมาชิก | ไม่ใช่ชั่วโมงฟังจริง |
| Free/Paid share | ชั่วโมงความยาวเพลงของ level / รวมชั่วโมงใน filter เดียวกัน | วันที่และระดับสมาชิก | ใช้ level ณ event ไม่ใช่สถานะล่าสุด |
| Top 10 artist/song | จำนวน NextSong จัดอันดับในแต่ละ daypart | daypart และคอนเทนต์ | ใช้ชื่อศิลปิน/เพลงจาก logs แม้ catalog ไม่พบ |
| Upgrade submissions | count(page = Submit Upgrade) | วันที่ | ไม่ใช่ unique converters หรือยอดชำระเงิน |
| Downgrade submissions | count(page = Submit Downgrade) | วันที่ | ไม่ใช่ Churn |
| Engagement decline | current 7 วันลดลง >=50% จาก prior 7 วัน | ผู้ใช้ ณ as_of_date | มีประวัติ >=14 วัน และ prior >=5 เพลง |
| Inactive 7d | ไม่มี NextSong >=7 วัน | ผู้ใช้ ณ as_of_date | มีประวัติ >=14 วัน; ถ้าติด decline ให้รายงาน decline ก่อน |

Daypart: night = 00:00–05:59, morning = 06:00–11:59, afternoon = 12:00–17:59, evening = 18:00–23:59

## Retention และการป้องกัน Data Leakage

รายงาน watchlist ใช้ `as_of_date = วันที่ล่าสุดในข้อมูล` และคำนวณย้อนหลังแบบรวมวัน cutoff: current = cutoff-6 ถึง cutoff, prior = cutoff-13 ถึง cutoff-7 ยังไม่ได้คำนวณ churn probability และยังไม่ควรส่งข้อเสนอส่วนลดอัตโนมัติ

วันแรก/วันสุดท้ายอาจมี logs ไม่ครบ 24 ชั่วโมง และไม่ทราบว่าการไม่ปรากฏใน logs คือไม่ใช้งานจริงหรือเก็บข้อมูลไม่ครบ ผลลัพธ์เป็น observation ใน sample นี้ ผู้ใช้ที่ประวัติสั้นจะเป็น `insufficient_history` ไม่ถูกบังคับเป็นกลุ่มปกติ

ถ้าเพิ่มชุด Churn: ต้องกำหนด account cancellation vs paid subscription cancellation แยกจาก downgrade, กำหนด prediction cutoff และ horizon เช่น 14 วัน, สร้าง features จาก events ก่อน cutoff เท่านั้น, ตรวจ right censoring, แบ่ง train/test ตามเวลา และประเมินกับ label จริงก่อนอ้างประสิทธิภาพ

## การเทียบหัวข้อกับวิชา

| เนื้อหาวิชา | สิ่งที่ทำในโปรเจกต์ |
|---|---|
| Week 3 KPI Layer | rpt_* และนิยาม KPI ด้านบน |
| Week 4 Star Schema | Fact events กับ conformed dimensions |
| Week 5 Snowflake | ไม่แยก location เป็น hierarchy เพราะข้อมูลไม่พอยืนยัน |
| Week 6 SCD | membership history แบบ Type 2 จากเวลาเกิด event |
| Week 7 Fact Table Design | transaction fact + periodic user-day snapshot |
| Week 8 Aggregation / OLAP | daily/monthly summary และ SQL roll-up / slice / dice |
| Week 9 Incremental | content hash dedup + incremental delete/insert ตาม unique_key |
| Week 10–11 Orchestration | DAG ตัวอย่างโหลด -> dbt build -> export แบบ manual trigger |

อ้างอิง [เนื้อหาวิชา](https://github.com/E27-25/dsba8-data-warehouse) สำหรับหลักการ ไม่ได้อ้างว่าใช้เครื่องมือครบทุก lab หรือ deploy Airflow/Cosmos แล้ว
