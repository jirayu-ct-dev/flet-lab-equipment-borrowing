# แผนระบบ MVP

เอกสารนี้ขยาย [project_scope.md](project_scope.md) ให้เป็นแบบที่นำไปพัฒนาได้ โดยไม่เพิ่มฟีเจอร์นอกขอบเขต

## โครงสร้าง

ระบบเป็น Flet Web process เดียว เชื่อม SQLite โดยตรงผ่าน `AppService` ไม่มี API server แยก ไม่มี repository abstraction และไม่มี Docker งานเขียนข้อมูลใช้ transaction ของ SQLite ส่วน LINE เป็น network boundary ที่เรียกหลัง transaction สำเร็จเท่านั้น

## แบบข้อมูล

- `faculties → departments → cohorts → class_groups`: ข้อมูลสังกัดแบบลำดับชั้น
- `users`: username, password hash, ชื่อ,อีเมลสำรอง, role, user type, สังกัด, status และ LINE User ID
- `equipment_categories → equipment_types → equipment_units`: หมวดหมู่ ชนิด และทรัพย์สินรายชิ้น
- `loans → loan_items`: หัวรายการยืมและอุปกรณ์แต่ละชิ้น การคืนเก็บ `returned_at` และผู้รับคืนที่ item

ไม่มีตาราง lost/damage/fine/payment/audit/notification log/queue

## เส้นทางงาน

### เข้าสู่ระบบ

1. username/password ตรวจ hash และสถานะบัญชี
2. ผู้ใช้ใหม่ถูกบังคับไปหน้าเปลี่ยนรหัสก่อนเข้าหน้าอื่น
3. LINE ที่ผูกแล้วเข้าสู่บัญชีเดิม
4. LINE ที่ยังไม่ผูกต้องยืนยัน username/password ก่อนบันทึก LINE User ID

### ยืม

Admin ค้นหาผู้ยืมและอุปกรณ์ เลือกหลายชิ้น ระบุวัน แล้วกดยืนยัน Service ตรวจผู้ใช้, overdue, วันที่, duplicate และสถานะทุก unit ภายใต้ `BEGIN IMMEDIATE`; ถ้าผ่านจึงสร้าง loan/items และเปลี่ยนทุก unit เป็น borrowed พร้อมกัน

### คืน

Admin เปิดรายการ active เลือก item ที่คืนครั้งนี้และยืนยัน Service บันทึกเวลาคืนรายชิ้น เปลี่ยน unit เป็น available และปิด loan เมื่อไม่มี item ค้าง

### LINE reminder

เมื่อ process เปิดและทุก 24 ชั่วโมง ระบบ claim รายการที่เหลือ 3 หรือ 1 วันตาม Asia/Bangkok โดยบันทึกเวลาลงคอลัมน์บน loan ก่อนส่ง จึงไม่ส่งซ้ำ การส่งล้มเหลวไม่ย้อนธุรกรรมและไม่มี retry

## หน้าจอ

- Admin: ภาพรวม, ยืม–คืน, ผู้ใช้, อุปกรณ์, ข้อมูลหลัก, ประวัติ, บัญชี
- ผู้ยืม: หน้าหลัก, ของที่ยืม, อุปกรณ์พร้อมยืม, ประวัติ, บัญชี

Desktop ใช้ sidebar; หน้าจอแคบใช้ bottom navigation เนื้อหาหลักเป็น card/list เดียวกันเพื่อไม่แยก code path
