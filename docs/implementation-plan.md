# แผนดำเนินงานและเกณฑ์ตรวจรับ

## 1. ฐานข้อมูลและบัญชี

- [x] Schema ใหม่ตรง scope และไม่มีตารางฟีเจอร์ที่ตัดออก
- [x] Admin เริ่มต้น `admin/admin1234` พร้อม forced password change
- [x] Username case-insensitive, validation และ inactive account
- [x] โครงสร้างคณะ/สาขา/รุ่น/หมู่เรียน

## 2. ผู้ใช้และ import

- [x] Admin สร้าง แก้ไข ปิด/เปิด และ reset password
- [x] CSV/XLSX template, preview, row errors และ duplicate protection
- [x] ประวัติรายบุคคล

## 3. อุปกรณ์และยืม–คืน

- [x] หมวด ชนิด และอุปกรณ์รายชิ้น
- [x] Transactional multi-item loan และ overdue guard
- [x] Partial return และ auto-complete
- [x] Dashboard/history สำหรับสอง role

## 4. LINE

- [x] LINE Login ผูกกับบัญชีเดิมหลังยืนยันรหัส
- [x] Unlink จากหน้าบัญชี
- [x] ข้อความยืมสำเร็จ คืนครบ และ reminder 3/1 วันแบบ best effort
- [x] Reminder dedupe บน loan

## 5. ตรวจรับ

- [x] Automated service/import tests
- [x] Browser smoke: login, forced password, responsive shell, CRUD dialogs, loan confirmation และ partial-return dialog
- [ ] LINE callback/push ทดสอบกับ channel จริง เพราะต้องใช้ secret และบัญชี LINE
