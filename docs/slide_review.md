# ผลอ่านสไลด์ Canva และรายการแก้ก่อนนำเสนอ

อ่านผ่าน Canva editor จำนวน **23 หน้า** วันที่ **25 ตุลาคม 2026** จาก [ลิงก์ที่ผู้ใช้ให้](https://www.canva.com/design/DAHV7HuYtu4/eldxlfLy_ReVvqPPnlqSUg/edit) เอกสารนี้เป็นข้อเสนอแนะสำหรับแก้สไลด์ โค้ดโปรเจกต์ไม่ได้เปลี่ยน Canva ต้นฉบับ

## สิ่งที่พบ

หน้า 1 เป็น checklist สิ่งที่ต้องมี หน้า 5–14 เป็นหัวข้อ/บริบท/คำถาม/แหล่งข้อมูล/มิติ/KPI/Bus Matrix หน้า 15 และ 17 เป็นบทพูด หน้า 16 เป็น Tech Stack ส่วนบางหน้าก่อนและหลังเนื้อหามี template placeholder ควรซ่อนออกจากเวอร์ชันนำเสนอ

| หน้า | ประเด็น | เนื้อหาที่ควรใช้แทน |
|---|---|---|
| 8 | คำถามการฟังตามเวลาและสัญญาณ Churn | วิเคราะห์เพลง/ศิลปินตามช่วง UTC และใช้ engagement screening เป็นงานปัจจุบัน แยก Churn เป็นส่วนต่อยอด |
| 9 | ตารางตัวอย่างมี Thumbs Up/Down, Add to Playlist, Cancellation | ระบุชัดว่าไม่มีใน ZIP ชุดจริง ใช้ page counts จาก reports/data_profile.json |
| 9 | แหล่งข้อมูลเขียน Kaggle/AWS แบบกว้าง | แหล่งที่ตรวจจริงคือ ZIP ที่ให้มา พร้อม SHA-256 ไม่ใส่ลิงก์ดาวน์โหลดที่ยังไม่ตรวจ |
| 9 | Upgrade = upgrade สำเร็จ | Upgrade คือ page view; Submit Upgrade คือ submission ไม่ใช่หลักฐานชำระเงิน |
| 10–12 | measures มี Skip / Like / Churn | เปลี่ยนเป็น event_count, is_songplay, played_track_duration_seconds, upgrade/downgrade submission |
| 10–12 | subscription ใน dim_user และ dim_subscription ซ้ำ | เก็บระดับสมาชิก ณ event ใน fact และแยก dim_user_subscription สำหรับประวัติ |
| 12 | dim_interaction เก็บการหยุด/ข้าม | เก็บ page ตามที่เกิดจริง พร้อมกลุ่ม navigation/streaming/subscription/error |
| 12 | location มีประเทศและพิกัด | เก็บสตริง location จาก log ไม่เดาข้อมูล geographic hierarchy |
| 13 | ชั่วโมงการฟังจริง | ใช้คำว่า Played track hours พร้อมหมายเหตุว่าเป็นผลรวมความยาวเพลง |
| 13 | Churn Funnel เปรียบเทียบ Dislike | เปลี่ยนเป็น engagement watchlist และเปิดเผยกฎ ไม่ทำ Funnel ที่ไม่มีขั้นตอนลำดับจริง |
| 13–14 | Ad Impressions และรายได้ | ย้ายเป็น future scope เพราะไม่มี exposure, revenue, price |
| 14 | Bus Matrix ครอบคลุมทุกมิติโดยไม่แยก grain | ใช้ matrix ใน docs/modeling.md และแยก transaction fact กับ user-day snapshot |
| 16 | หลายเครื่องมือยังไม่เลือก | ปัจจุบันใช้ Python + dbt + DuckDB; มี PostgreSQL/Metabase Compose และ DAG template โดยรายงานสถานะรันจริงใน validation.md |

## โครงร่างนำเสนอที่ใช้ได้ทันที

1. ชื่อเรื่องและปัญหาธุรกิจ: ทีมเพลงต้องรู้ความนิยมตามเวลา ทีมสมาชิกต้องติดตาม engagement
2. Data Source & Profile: 8,056 events, 14,896 catalog rows, พ.ย. 2018 UTC, ตัวอย่าง JSON ที่ตัด personal fields และข้อจำกัด
3. Subject Area / Process / KPI: ใช้ตารางใน requirements.md พร้อมนิยาม active และ track hours
4. Grain และ Schema: transaction fact 1 event และ snapshot fact 1 user/day พร้อม ERD
5. Bus Matrix: แสดง conformed dimensions และ future scope ให้แยกชัด
6. Data Dictionary: keys, types, null handling, measure semantics และ source mapping
7. ผลจริง: ใช้ summary.json และ CSV; แยก measured KPI จาก heuristic screening
8. Tech Stack และ Demo: รัน pipeline, ดู dbt tests และเปิด SQL ใน BI

หากต้องการสรุปเหลือ 5 หน้า ให้รวมข้อ 3–5 และย้าย Data Dictionary เป็นภาคผนวก ไม่ควรตัดคำจำกัดความ track hours/Churn ออก
