---
name: docker-deployment-standards
description: Build, edit, or review Dockerfiles and Docker Compose deployments with reproducible builds, small runtime images, safe configuration, service readiness, and migration ordering. Use for containerizing or deploying applications with Docker or Compose; do not use for UI-only work.
---

# Docker Deployment Standards

ปรับแนวทางให้เข้ากับ architecture, framework, deployment target และ conventions ของ
โปรเจกต์ก่อนเสมอ แก้เฉพาะส่วนที่ requirement ต้องการและตรวจเส้นทาง build กับ startup
จริงตั้งแต่ต้นจน service พร้อมรับ traffic

## Build images

- ใช้ multi-stage build เมื่อช่วยแยก build dependencies และ source ออกจาก runtime image
- ตรึง base image เป็น version ที่ตั้งใจใช้ ไม่ใช้ floating tag เช่น `latest`
- ติดตั้ง dependencies ผ่าน lockfile และคำสั่ง frozen/immutable ของ package manager
- เรียง layer ให้ manifest และ dependency installation cache ได้ก่อน copy source
- ใช้ `.dockerignore` ตัด `.git`, `.env`, dependencies, build output, test artifacts และ
  local storage ที่ไม่ควรเข้า build context
- รัน production artifact หรือ production server ใน runtime stage ไม่รัน dev server
- ใช้ non-root user เมื่อ base image และ runtime รองรับโดยไม่ทำให้ permission พัง

## Configuration and secrets

- ห้าม bake secret ลง image หรือส่งผ่าน build argument ที่คงอยู่ใน layer/history
- ส่ง runtime configuration ผ่าน secret manager, environment หรือ `env_file` ตามระบบ
- แยก address ฝั่ง host ออกจาก container network; service-to-service ใช้ DNS name ของ
  Compose/Kubernetes แทน `localhost`
- ตรวจว่า client-visible build-time variables ไม่มี server secret ปะปน

## Startup and readiness

- ใช้ healthcheck/readiness check ที่ตรวจ dependency หรือ HTTP endpoint เบาอย่างเหมาะสม
- เมื่อ startup ต้องรอฐานข้อมูล ให้รอ readiness ไม่ใช่แค่ container started
- หากระบบต้อง migrate ก่อน app start ให้ใช้ one-shot migration job/service หรือกลไก
  deployment ที่ทำให้ migration สำเร็จก่อนเริ่มรับ traffic
- อย่ารัน migration พร้อมกันจาก app replicas หลายตัว เว้นแต่ migration tool รองรับชัดเจน
- ตั้ง restart policy ตามชนิด workload; job แบบ one-shot ไม่ควรถูก restart แบบ daemon

## Verification

- Build จาก clean context ด้วย lockfile
- ตรวจ runtime image ว่าไม่มี `.env`, source หรือ build-only dependencies ที่ไม่จำเป็น
- Start stack ใหม่ตั้งแต่ไม่มี container และยืนยันลำดับ database → migration → app
- ตรวจ health/readiness, graceful shutdown, logs และการ restart หลัง failure
- รัน application smoke test ผ่าน port/network เดียวกับ production topology
