# Security — Field Notes CMS

สรุปผลการตรวจสอบความปลอดภัย (security review) และมาตรการที่ใส่ไว้ในระบบ
อ้างอิงหมวดหมู่ OWASP Top 10

## มาตรการที่ทำแล้ว ✅

| หมวด | ความเสี่ยง | สิ่งที่ทำ |
|---|---|---|
| **A01 Broken Access Control** | เข้าหลังบ้านได้โดยไม่ล็อกอิน / open redirect | ทุก route `/admin` ผ่าน `@login_required`; ดราฟต์เห็นเฉพาะตอนล็อกอิน; `?next=` รับเฉพาะ path ภายใน (กัน open-redirect) |
| **A02 Cryptographic** | รหัสผ่าน/คุกกี้รั่ว | รหัสผ่าน hash ด้วย `pbkdf2:sha256`; `secret_key` สุ่ม 256-bit เก็บถาวร; คุกกี้ `HttpOnly` + `SameSite=Lax` + `Secure` (เมื่อ HTTPS) |
| **A03 Injection (SQLi)** | ยิง SQL ผ่าน input | ทุก query ใช้ parameterized `?` ไม่มีการต่อ string จาก user |
| **A03 Injection (XSS)** | ฝัง `<script>` ผ่าน caption/title | Jinja autoescape เปิดทุกหน้า; แทน `\|safe` ที่อันตรายด้วย filter `nl2br` ที่ escape ก่อนเสมอ |
| **A05 Misconfiguration** | debugger รั่ว / header อ่อน | `debug` ปิดใน production (gunicorn); ส่ง security headers ทุก response (ดูล่าง); error page ไม่โชว์ stack trace |
| **CSRF** | เว็บปลอมสั่งลบ/แก้ขณะล็อกอินอยู่ | CSRF token (double-submit) บังคับทุกฟอร์ม POST ของ admin + `SameSite=Lax` เป็นชั้นที่สอง |
| **File upload** | อัปไฟล์อันตราย / decompression bomb / DoS | จำกัด 40MB/ไฟล์; ตรวจนามสกุล + `verify()`; รี-เอ็นโค้ดเป็น JPEG ใหม่ (ลอก payload/EXIF); จำกัดพิกเซล 120MP; ตั้งชื่อไฟล์เองด้วย UUID (กัน path traversal) |
| **Brute force** | เดารหัสผ่านรัว ๆ | ล็อก login 7 ครั้งผิดใน 15 นาที + rotate session id ตอนล็อกอินสำเร็จ (กัน session fixation) |
| **Path traversal** | `/uploads/../../etc` | ใช้ `send_from_directory` (Werkzeug กัน `../` ให้อยู่แล้ว) |

### Security headers ที่ส่งทุก response
`X-Content-Type-Options: nosniff` · `X-Frame-Options: DENY` (กัน clickjacking) ·
`Referrer-Policy` · `Permissions-Policy` · `Content-Security-Policy` (จำกัดให้โหลดได้แค่
ตัวเอง + Google Fonts, ห้าม script ภายนอก/iframe) · `Strict-Transport-Security` (เมื่อ HTTPS)

## สิ่งที่เจ้าของต้องทำ 🔑

1. **ตั้งรหัสผ่านที่เดายาก** (ขั้นต่ำ 8 ตัว ระบบบังคับแล้ว แต่ควรยาว/ผสม) ครั้งแรกที่เข้า `/admin`
2. **ห้ามตั้ง `FN_DEBUG`** บนเครื่อง production เด็ดขาด (Werkzeug debugger = รันโค้ดได้)
3. ตอน deploy ให้ตั้ง **`FN_HTTPS=1`** (ใน `render.yaml` ตั้งให้แล้ว) เพื่อเปิดคุกกี้ Secure + HSTS
4. ให้ host อยู่หลัง **HTTPS เสมอ** (Render/Cloudflare ให้ฟรี)
5. สำรอง `data/` + `uploads/` สม่ำเสมอ

## ความเสี่ยงที่ยอมรับได้ (ตามขนาดโปรเจกต์)

- **Login throttle เป็นแบบ in-memory ต่อ worker** — เพียงพอสำหรับเว็บทราฟฟิกต่ำ; ถ้าต้องการเข้มกว่านี้ค่อยย้ายไปเก็บใน DB/Redis
- **CSP ยังมี `'unsafe-inline'`** เพราะดีไซน์เป็น single-file (CSS/JS ฝังในหน้า) — แลกกับความเรียบง่าย; ถ้าจะตัดออกต้องแยกไฟล์ + ใช้ nonce
- **`/subscribe` ไม่มี rate limit/captcha** — เสี่ยงโดน spam อีเมลปลอม (ความเสี่ยงต่ำ ไม่มี privileged action)
