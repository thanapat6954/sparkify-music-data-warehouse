# สไลด์นำเสนอ Sparkify Data Warehouse

- [Canva ฉบับแก้ไขได้ 16 หน้า](https://www.canva.com/design/DAHY9wZeZuM/fBo_PprIkXw2f_m0DnZE-A/edit)
- [PowerPoint สำรอง](sparkify-presentation.pptx) มี native tables, diagrams, charts และ speaker notes
- [Dashboard จริงบนเครื่อง](http://localhost:23000/dashboard/2)

Canva เป็นฉบับที่ปรับแกน ขนาดฟอนต์ และตำแหน่งกราฟหลัง import แล้ว ส่วน PowerPoint ใช้รูปแบบ native ที่ตรวจสอบแยกต่างหาก เนื้อหาและแหล่งข้อมูลตรงกัน

## ลำดับเนื้อหา

1. ชื่อโครงการ
2. บริบทธุรกิจและคำถาม
3. Dataset และสิ่งที่ข้อมูลรองรับ
4. Subject Area, Business Process, KPI และ Grain
5. สถาปัตยกรรม Pipeline
6. Star Schema
7. Bus Matrix
8. Data Dictionary
9. SCD Type 2 และ late arrival
10. ภาพรวมการฟัง Free/Paid
11. DAU รายวัน
12. ช่วงเวลาที่มี Songplays มากที่สุด (UTC)
13. ศิลปินยอดนิยมใน sample
14. Engagement screening
15. ผลการพัฒนาและข้อจำกัด
16. ลำดับ Demo

ใช้เวลาประมาณ 10–15 นาที ส่วนคำอธิบายและ source citations อยู่ใน speaker notes ของ PowerPoint ควรอธิบายว่า track hours เป็นผลรวมความยาวเพลง และ watchlist ไม่ใช่จำนวนผู้ที่ยกเลิกสมาชิก

## ภาพประกอบ

ภาพหน้าปก `assets/headphones-cover.png` สร้างด้วย built-in ImageGen เพื่อใช้เป็นภาพตกแต่ง ไม่ใช่ภาพจาก dataset ส่วน `assets/metabase-dashboard.png` เป็น screenshot ของระบบที่เชื่อม PostgreSQL จริง

Prompt ภาพหน้าปก:

> Use case: product-mockup. Create one wide 16:9 editorial photograph for a university music streaming data warehouse presentation cover. A single pair of premium matte black over-ear headphones lies sculpturally on a warm ivory stone surface, entirely in the RIGHT half of the composition. Subtle warm coral side light and charcoal shadows. Left half is clean uninterrupted warm ivory negative space for editable slide typography. Restrained sophisticated analogue music aesthetic, real soft studio lighting, excellent material detail, no people. No text, logos, charts, interface, watermark or brand marks.
