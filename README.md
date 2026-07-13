# Field Notes CMS

ระบบหลังบ้านสำหรับเว็บ photo essay **Field Notes** — ให้เจ้าของ (BUN) ลงเรื่องเองได้
(อัปโหลดรูป เขียนคำบรรยายไทย/อังกฤษ จัดลำดับภาพ กดเผยแพร่) และมี dashboard
สถิติผู้เข้าชมแบบเคารพความเป็นส่วนตัว

> A self-hosted CMS + privacy-friendly analytics for the Field Notes photo-essay
> site. Python + Flask + SQLite + Pillow. No build step, no external services.

---

> เนื้อหาเว็บเป็น **ภาษาอังกฤษล้วน** (single-language) หน้า admin เป็นอังกฤษ
> เอกสารนี้เขียนไทยไว้ให้เจ้าของอ่านสะดวก

## ทำอะไรได้บ้าง

- **หน้าเว็บสาธารณะ** เรนเดอร์จากฐานข้อมูล — หน้าแรก (editorial light theme) +
  หน้า essay (dark scrollytelling)
- **หลังบ้าน (`/admin`)** ล็อกอินด้วยรหัสผ่านเดียว แก้ได้ **ทุกส่วนของเว็บ**:
  - **Essays** — สร้าง/แก้ไข/ลบ photo essay, อัปโหลดรูปต้นฉบับ (ระบบย่อ+บีบอัดอัตโนมัติ
    ด้วย Pillow: plate ≤1900px, hero ≤2200px, gallery/card ≤1400px), เขียนคำบรรยาย,
    เลือกภาพเต็มจอ/ปกติ, สลับลำดับ, ใส่ข้อความคั่น (interlude), ฉบับร่าง→เผยแพร่
  - **Site content** (`/admin/site`) — แก้ hero / about (แนะนำตัว) / footer ทั้งข้อความและรูป
  - **Archive** (`/admin/gallery`) — จัดการแกลเลอรี "From the archive": อัปโหลดหลายรูปพร้อมกัน,
    ใส่ caption, เรียงลำดับ, ลบ (มีผลกับเว็บทันที)
  - **ตัวอย่างก่อนเผยแพร่** — การแก้เนื้อหา essay/site จะสะสมเป็น **ฉบับร่าง** แก้ได้หลายจุด
    แล้ว **Preview all changes** ครั้งเดียวบนหน้าเว็บจริง ก่อนกด **Publish** ทั้งชุด
- **สถิติผู้เข้าชม (`/admin/stats`)** — ยอดเข้าชม, ผู้เข้าชมไม่ซ้ำ, กราฟรายวัน,
  essay ยอดนิยม, referrer, ประเทศ, อุปกรณ์/เบราว์เซอร์
  - **ไม่เก็บ IP ไม่ใช้คุกกี้ ไม่ตามรอยรายบุคคล** — นับผู้เข้าชมไม่ซ้ำด้วยวิธี
    daily-salted hash (เหมือน Plausible) ที่ย้อนกลับไปหาตัวบุคคลไม่ได้

---

## รันบนเครื่อง (local)

ต้องมี Python 3.9+ (เครื่องนี้ใช้ `/usr/bin/python3` ได้)

```bash
cd field-notes-cms
python3 -m pip install --user -r requirements.txt   # ติดตั้ง Flask, Pillow, gunicorn
python3 seed.py                                      # นำเข้า essay Skardu (ทำครั้งเดียว)
./run.sh start                                       # เปิดเว็บ http://localhost:8000
```

> ⚠️ **อย่าใช้ `python3 app.py` เป็นเว็บจริง** — มันเป็น dev server ที่จะ **ดับทันที
> เมื่อปิดหน้าต่าง terminal** (นี่คือสาเหตุที่ก่อนหน้านี้ "เว็บใช้ไม่ได้")
> ใช้ `./run.sh` แทน — มันรันด้วย gunicorn แบบ background ที่ **อยู่ค้างแม้ปิด terminal**

จัดการเซิร์ฟเวอร์ด้วย:

```bash
./run.sh start      # เปิด (ถ้าเปิดอยู่แล้วจะไม่ทำซ้ำ)
./run.sh status     # เช็คว่ายังทำงานอยู่ไหม + health check
./run.sh restart    # ปิดแล้วเปิดใหม่ (ใช้หลังแก้โค้ด)
./run.sh stop       # ปิด
./run.sh logs       # ดู log สด
PORT=9000 ./run.sh start   # เปลี่ยนพอร์ต
```

ครั้งแรกที่เข้า `http://localhost:8000/admin` ระบบจะให้ **ตั้งรหัสผ่าน** เอง
(เก็บไว้ให้ดี) ลืมรหัสเมื่อไหร่ตั้งใหม่ได้:

```bash
python3 set_password.py 'รหัสใหม่ของคุณ'
```

---

## โครงสร้าง

```
field-notes-cms/
├── app.py            ← Flask app + ทุก route
├── db.py             ← การเชื่อมต่อ SQLite
├── images.py         ← ย่อ/บีบอัดรูปด้วย Pillow
├── analytics.py      ← เก็บสถิติแบบ privacy-friendly + query สรุป
├── schema.sql        ← โครงตาราง
├── seed.py           ← นำเข้า essay Skardu เดิม (รันครั้งเดียว)
├── set_password.py   ← ตั้ง/รีเซ็ตรหัสผ่าน admin
├── templates/        ← Jinja templates (landing, essay, admin/*)
├── static/images/    ← รูปหน้าแรก (hero, gallery, about ฯลฯ)
├── data/app.db       ← ฐานข้อมูล (ไม่ commit — อยู่ใน .gitignore)
└── uploads/          ← รูปที่อัปโหลด (ไม่ commit)
```

`data/` และ `uploads/` คือข้อมูลจริงทั้งหมด — **สำรองสองโฟลเดอร์นี้ไว้เสมอ**

---

## ขึ้นออนไลน์ (deploy)

แอปนี้เป็น Python/Flask มาตรฐาน รันบน host ไหนก็ได้ที่รัน Python ค้างไว้ได้
**ข้อสำคัญที่สุด:** `data/` (ฐานข้อมูล) และ `uploads/` (รูป) ต้องอยู่บน
**ดิสก์ถาวร (persistent disk/volume)** — ไม่งั้นรูปกับสถิติจะหายทุกครั้งที่ deploy ใหม่

ใช้ env var ชี้ตำแหน่งเก็บข้อมูลไปที่ดิสก์ถาวร:

| env var | ค่าเริ่มต้น | ใช้ทำอะไร |
|---|---|---|
| `FN_DB_PATH` | `data/app.db` | ที่อยู่ไฟล์ฐานข้อมูล |
| `FN_UPLOAD_DIR` | `uploads/` | โฟลเดอร์เก็บรูปที่อัปโหลด |
| `PORT` | `8000` | พอร์ต (host ส่วนใหญ่ตั้งให้อัตโนมัติ) |

### Render (แนะนำ — มี `render.yaml` ให้แล้ว)

1. push โฟลเดอร์นี้เป็น git repo ขึ้น GitHub
2. Render → New + → **Blueprint** → เลือก repo (อ่าน `render.yaml` อัตโนมัติ)
3. ใช้ plan **Starter** ขึ้นไป (มี persistent disk — plan Free ไม่มี รูปจะหาย)
4. deploy เสร็จเปิด `https://<your-app>.onrender.com/admin` แล้วตั้งรหัสผ่าน

### Railway / Fly.io / VPS

- คำสั่งรัน production: `gunicorn app:app --workers 2 --bind 0.0.0.0:$PORT`
  (มีใน `Procfile` แล้ว)
- ตั้ง `FN_DB_PATH` / `FN_UPLOAD_DIR` ให้ชี้ไป volume ถาวรที่ mount ไว้
- รัน `python seed.py` หนึ่งครั้งหลัง deploy แรก (หรือปล่อยว่างแล้วสร้างเรื่องเองใน admin)

### ประเทศของผู้เข้าชม

คอลัมน์ "ประเทศ" จะเป็น `XX` (ไม่ทราบ) เว้นแต่มี CDN/พร็อกซีคั่นหน้าที่ส่ง header
ประเทศมาให้ — ถ้าวาง **Cloudflare** หน้าเว็บ (ฟรี) จะได้ `CF-IPCountry` อัตโนมัติ
และสถิติประเทศจะแม่นทันที (โดยที่แอปยังไม่เก็บ IP เอง)

---

## หมายเหตุทางเทคนิค

- Werkzeug ใช้ `scrypt` เป็นค่า default ในการ hash รหัสผ่าน แต่ Python ของ macOS
  Command Line Tools ไม่มี `hashlib.scrypt` — โค้ดจึงระบุ `method="pbkdf2:sha256"`
  ไว้ชัดเจน (ใช้ได้ทุกเครื่อง)
- SQLite เปิดโหมด WAL รองรับการอ่านพร้อมกันได้ดี เหมาะกับบล็อกทราฟฟิกไม่สูง
- รูปต้นฉบับความละเอียดสูง (เช่นไฟล์ Sony A7IV 25–50MB) อัปโหลดได้เลย — เพดานต่อไฟล์
  40MB (ปรับใน `app.py` ที่ `MAX_CONTENT_LENGTH`)

## เว็บใช้ไม่ได้? (troubleshooting)

1. `./run.sh status` — ถ้าขึ้น ⛔ not running ให้ `./run.sh start`
2. เปิดไม่ได้แต่ status ขึ้น ✅ → `./run.sh restart` แล้วดู `./run.sh logs`
3. ขึ้น "missing dependencies" → `python3 -m pip install --user -r requirements.txt`
4. พอร์ตชนกับโปรแกรมอื่น → `PORT=9000 ./run.sh start`

**ทางแก้ถาวรที่สุด:** เครื่อง laptop ไม่เหมาะเป็นเว็บเซิร์ฟเวอร์ตลอด 24 ชม. — deploy
ขึ้น Render (ดูหัวข้อ "ขึ้นออนไลน์") แล้วเว็บจะ **เปิดตลอดเวลาเองโดยไม่ต้องสั่ง start**
และไม่มีทางดับเพราะปิดเครื่อง/ปิด terminal อีก
