# Field Notes CMS — Handoff for Claude Code

> อ่านไฟล์นี้ให้จบก่อนแตะอะไรก็ตาม เอกสารนี้เขียนให้ Claude Code session ในอนาคต
> เข้าใจโปรเจกต์นี้ได้ครบโดยไม่ต้องถามเจ้าของซ้ำ
>
> **Owner:** BUN (mrsobanali786@gmail.com) — สื่อสารภาษาไทย
> **Live site (หลัก — ยืนยันแล้วว่า Live):** https://fieldnotes-pph8.onrender.com
>   (`fieldnotes` เฉย ๆ ชนกับคนอื่นบน Render จริงตามที่เตือนไว้ → ระบบเติม `-pph8` ให้อัตโนมัติ
>   — `render.yaml` ยังคงเขียน `name: fieldnotes` เพราะเป็นแค่ค่าที่ *ขอ*ไว้ ไม่ใช่ผลลัพธ์จริงเสมอไป)
> **Live site (legacy — จะยกเลิกเมื่อหมดอายุ):** https://bunniee.pythonanywhere.com
>   (PythonAnywhere free tier หมดอายุทุก 1 เดือนถ้าไม่กดต่ออายุ — เจ้าของตัดสินใจแล้วว่า
>   **จะปล่อยให้หมดอายุไปเอง ไม่ต่อ** เมื่อครบกำหนดครั้งถัดไป ไม่ต้องปิดมือ)
> **GitHub:** https://github.com/mamamiya2114/field-notes-website
> **Last updated:** 2026-07-16 (commit `c70dfb6`)
>
> ⚠️ Render คือเว็บจริงตอนนี้ — แต่ PythonAnywhere **ยังออนไลน์อยู่จนกว่าจะหมดอายุ** อย่าเพิ่ง
> ถือว่าตายแล้ว ถ้า debug อะไรเกี่ยวกับ production ให้ถามเจ้าของว่าหมายถึง URL ไหนเสมอ

---

## 1. โปรเจกต์นี้คืออะไร

**Field Notes** — เว็บ photo-essay ส่วนตัวของ BUN ช่างภาพ/นักวิจัย ที่มีระบบหลังบ้าน (CMS)
ให้เจ้าของลงงานเองได้โดยไม่ต้องแตะโค้ด

- **หน้าสาธารณะ:** landing (editorial light theme) · หน้า essay (dark scrollytelling) ·
  `/essays` (หน้ารวมทุก essay ที่ publish แล้ว — เพิ่มใหม่ 2026-07 เพื่อรองรับ essay ที่ 2 ขึ้นไป
  โดยไม่ทำให้หน้าแรกรก: featured 1 + "More essays" สูงสุด 3 การ์ด แล้วค่อยลิงก์ไป `/essays`)
- **หลังบ้าน `/admin`:** สร้าง/แก้ essay, แก้เนื้อหาหน้าแรก (รวม About + ปุ่ม "Get in touch"
  LinkedIn/email ที่เพิ่มใหม่), จัดการ archive gallery, ดูสถิติ
- **เนื้อหาหลักปัจจุบัน:** photo essay 1 เรื่อง — *"Life that does not stop, even with war
  within arm's reach"* (Skardu, Pakistan, พฤษภาคม 2025) 17 ภาพ + 1 interlude ถ่ายช่วง
  ความขัดแย้งอินเดีย–ปากีสถานปะทุ
- **UX เพิ่มเติม (2026-07):** swipe ซ้าย/ขวาใน lightbox บนมือถือ, lazy-load รูปใต้ fold,
  placeholder แทน broken-image icon เมื่อ essay ไม่มี hero, cache header รูปภาพยาวขึ้น
  (ดู §7.4 สำหรับรายละเอียดและเหตุผล)

**สแต็ก:** Python 3 + Flask + SQLite + Pillow · ไม่มี build step · ไม่มี JS framework ·
CSS/JS ฝังในไฟล์ HTML (single-file pages)

### ประวัติโดยย่อ (สำคัญต่อการเข้าใจ code)

โปรเจกต์นี้ผ่านการรื้อใหญ่หลายรอบ — ถ้าเจอโค้ด/ข้อมูลที่ดูขัดกัน ให้ยึดสถานะปัจจุบัน:

1. เริ่มจากเว็บ **static HTML เขียนมือ** (ตอนนี้เป็น legacy → `../field-notes/_LEGACY.md`)
2. สร้าง **Flask CMS** ขึ้นมาแทน (เพราะเจ้าของอยากลงงานเองได้ + ดูสถิติ)
3. **Security hardening** (CSRF, headers, upload guard ฯลฯ)
4. **รื้อใหญ่:** เว็บเป็น **ภาษาอังกฤษล้วน** (เดิม 2 ภาษา), **ถอดระบบ subscribe ทิ้ง**,
   เพิ่ม **preview-before-confirm**
5. เพิ่ม **archive gallery จัดการผ่าน admin** + **note ต่อรูป**
6. Deploy ขึ้น **PythonAnywhere (free tier)**

---

## 2. โครงสร้างไฟล์

```
field-notes-website/          ← repo root = โค้ดทั้งหมดอยู่ที่นี่เลย (ไม่มีโฟลเดอร์ซ้อน!)
├── CLAUDE.md                 ← ไฟล์นี้
├── README.md                 ← คู่มือใช้งาน (ภาษาไทย, สำหรับเจ้าของ)
├── SECURITY.md               ← สรุปมาตรการความปลอดภัย (OWASP)
│
├── app.py                    ← Flask app: ทุก route + changeset engine + site content
├── db.py                     ← SQLite connection + migrations (idempotent)
├── images.py                 ← Pillow: ย่อ/บีบอัด/validate รูปอัปโหลด
├── analytics.py              ← สถิติ privacy-friendly (ไม่เก็บ IP ไม่ใช้คุกกี้)
├── schema.sql                ← โครงตาราง (CREATE IF NOT EXISTS ทั้งหมด)
├── seed.py                   ← นำเข้า essay Skardu (idempotent, ข้ามถ้ามีแล้ว)
├── set_password.py           ← CLI รีเซ็ตรหัสผ่าน admin
├── run.sh                    ← ตัวจัดการเซิร์ฟเวอร์ local (start/stop/restart/status/logs)
│
├── requirements.txt          ← Flask, Pillow, gunicorn
├── Procfile / render.yaml    ← สำหรับ Render — **กลับมาใช้งานจริงแล้ว 2026-07** (ดู §5)
│                                render.yaml: name: fieldnotes ← กำหนด URL .onrender.com
│
├── templates/
│   ├── landing.html          ← หน้าแรก (hero, featured, "More essays" ≤3 การ์ด,
│   │                             archive gallery + lightbox+swipe, about+contact, footer)
│   ├── essays.html           ← หน้ารวมทุก essay ที่ publish (เพิ่มใหม่ 2026-07)
│   ├── essay.html            ← หน้า essay (dark scrollytelling)
│   ├── 404.html
│   └── admin/
│       ├── base.html         ← layout + nav + submit-loading JS
│       ├── login.html        ├── dashboard.html   ├── editor.html
│       ├── site.html         ├── gallery.html     └── stats.html
│
├── static/images/            ← 15 ไฟล์: about.jpg, hero-valley.jpg, pano-indus.jpg, g01–g12
├── seed_images/              ← 18 ไฟล์ p00-hero..p17-town (ต้นฉบับ essay Skardu สำหรับ seed)
│
├── data/                     ← ⛔ gitignored — ฐานข้อมูล app.db
├── uploads/                  ← ⛔ gitignored — รูปที่อัปโหลดผ่าน admin
├── logs/ · run/              ← ⛔ gitignored — log + pidfile ของ run.sh
```

> **สำคัญ:** repo root **คือ** โฟลเดอร์ `field-notes-cms` เดิม — ไม่มีโฟลเดอร์
> `field-notes-cms/` ซ้อนอยู่ข้างใน (เคยพลาดตรงนี้ตอน deploy)

---

## 3. ฐานข้อมูล (SQLite)

`schema.sql` เป็น `CREATE IF NOT EXISTS` ทั้งหมด + migration ใน `db.py` รันทุกครั้งที่ `init_db()`
(idempotent ปลอดภัยที่จะรันซ้ำ)

| ตาราง | คอลัมน์ | หมายเหตุ |
|---|---|---|
| `essays` | id, slug, **title**, kicker, location, date_text, **summary**, lede, outro, signature, hero_image, status, created_at, updated_at, published_at | `status` = draft \| published · title ขึ้นบรรทัดใหม่ได้ (`\n` → `<br>`) |
| `plates` | id, essay_id, position, kind, image, layout, **caption**, alt | `kind` = photo \| interlude · `layout` = normal \| full |
| `gallery` | id, position, image, alt, **note**, created_at | archive บนหน้าแรก · `image` = `/static/images/gNN.jpg` (default) หรือ `/uploads/gallery/…` |
| `site_content` | key, value | เนื้อหาหน้าแรก (hero/about/footer) — ว่าง = ใช้ `SITE_DEFAULTS` ใน app.py |
| `pending_edits` | token, kind, payload, created_at | **changeset** ที่ยังไม่ publish (ดู §4) · `kind` เก็บ *target* · `payload` = JSON list ของ ops |
| `visits` | id, day, ts, path, essay_slug, referrer, country, device, browser, visitor_hash | ไม่มี IP |
| `settings` | key, value | `admin_password` (pbkdf2 hash), `secret_key` |
| `daily_salts` | day, salt | salt รายวันสำหรับนับ unique visitor (ลบอัตโนมัติหลัง 60 วัน) |

### Migrations ใน `db.py` (รันอัตโนมัติ)
- `_migrate_english_only()` — เปลี่ยนจากสคีมา 2 ภาษาเดิม (`title_th`/`title_en`,
  `caption_th`/`caption_en`, `summary_en`) → คอลัมน์เดียว · ลบตาราง `subscribers` ทิ้ง
- `_migrate_gallery_note()` — เพิ่มคอลัมน์ `gallery.note`
- `_seed_gallery()` — ครั้งแรกเท่านั้น: เติม gallery จากไฟล์ `static/images/gNN.jpg` ที่มี

**ถ้าจะเพิ่มคอลัมน์ใหม่:** เขียนใน `schema.sql` (สำหรับ DB ใหม่) **และ** เขียน migration
`ALTER TABLE` ใน `db.py` (สำหรับ DB ที่มีอยู่แล้วบน production) — ต้องทำทั้งสองที่

> **ข้อยกเว้นที่ไม่ต้อง migration:** `site_content` เป็น key-value ทั่วไปอยู่แล้ว —
> การเพิ่ม key ใหม่ (เช่น `about_email`, `about_linkedin` ที่เพิ่มเข้า `SITE_DEFAULTS` ใน
> app.py ปี 2026-07) **ไม่ต้องแก้ schema/migration เลย** เพราะ `get_site()` merge
> `SITE_DEFAULTS` กับแถวที่มีอยู่จริงเสมอ (ดู §4.2) — รูปแบบนี้ใช้ได้กับ site-level
> settings ใหม่ ๆ ในอนาคตด้วย

---

## 4. สถาปัตยกรรมที่ต้องเข้าใจก่อนแก้โค้ด

### 4.1 Changeset — draft → preview → publish

**หัวใจของระบบแก้ไข** เจ้าของบ่นว่าเดิม "แก้ 1 อย่าง = ยืนยัน 1 ครั้ง" น่ารำคาญ จึงทำใหม่เป็น
**ชุดการแก้ (changeset) ต่อเป้าหมาย**:

- **target** = `"essay:<id>"` หรือ `"site"` (1 target = 1 changeset)
- `session["pending"]` = dict map `target → token` (payload ใหญ่เกิน cookie จึงเก็บใน SQLite)
- `pending_edits.kind` เก็บ **target** (ชื่อคอลัมน์ทำให้เข้าใจผิดได้), `payload` = JSON list ของ **ops**
- แต่ละ op: `{"kind": "essay_meta"|"essay_hero"|"plate_update"|"plate_replace"|"plate_add"|"site", "payload": {...}}`

**ฟังก์ชันหลักใน app.py:** `stage_op()` · `get_changeset()` · `unstage_kind()` · `drop_changeset()`
· `_apply_ops_to_context()` (เรนเดอร์ preview แบบ virtual) · `preview_confirm()` (เขียนลง DB จริง)

**กติกาการ merge ops:**
- `essay_meta`, `essay_hero`, `site` = **singleton** (แก้ใหม่ทับของเก่า, ไฟล์ที่ staged ไว้ถูกลบ)
- `plate_update`, `plate_replace` = singleton **ต่อ plate**
- `plate_add` = **ต่อท้ายเสมอ**
- กด Save โดยไม่ได้เปลี่ยนอะไร → ระบบตรวจจับและไม่สร้าง draft ขยะ

**ไฟล์รูปที่ staged:** อัปโหลดแล้วประมวลผลเป็นไฟล์จริงทันที (path อยู่ใน `payload["_new_files"]`)
→ ถ้ากด **Discard** ไฟล์เหล่านี้จะถูกลบทิ้ง

**สิ่งที่ *ไม่* ผ่าน changeset (มีผลทันที + มี confirm() dialog):**
plate move/delete · essay publish/unpublish/delete · **ทุกอย่างใน archive gallery**

### 4.2 Site content (หน้าแรก)
`SITE_DEFAULTS` ใน app.py = ข้อความ default · ตาราง `site_content` เก็บเฉพาะที่เจ้าของแก้ ·
ค่าว่าง = fallback กลับไป default (section ไม่มีทางว่างเปล่า) · `get_site()` merge ให้
รูป hero/about อัปโหลดได้ → เก็บเป็น `/uploads/site/…`

### 4.3 Jinja filters ที่เขียนเอง (ห้ามใช้ `|safe` ตรง ๆ)
- `nl2br` — escape ก่อน แล้วค่อยแปลง `\n` → `<br>` (กัน stored XSS)
- `emphasize` — escape ก่อน แล้ว `*คำ*` → `<em>คำ</em>` (ใช้กับ hero headline)

### 4.4 Analytics
นับแบบ Plausible: `visitor_hash = sha256(day + daily_salt + ip + ua)` — **ไม่เก็บ IP**,
salt เปลี่ยนทุกวันและถูกลบทิ้งหลัง 60 วัน (ย้อนกลับหาตัวบุคคลไม่ได้) ·
กรอง bot ทิ้ง · **ไม่นับ visit ของ admin ที่ล็อกอินอยู่**

### 4.5 Security (ดู SECURITY.md ประกอบ)
CSRF token บังคับ **ทุกฟอร์ม POST ของ admin** (`before_request` เช็ค) — **ถ้าเพิ่มฟอร์มใหม่แล้วลืมใส่
`<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` จะได้ 400 ทันที** ·
SameSite=Lax + HttpOnly + Secure (เมื่อ `FN_HTTPS=1`) · security headers + CSP ·
login throttle (7 ครั้ง/15 นาที) · upload: verify() + re-encode + จำกัด 120MP/40MB + ชื่อไฟล์ UUID

---

## 5. Deployment — **Render คือหลักแล้ว, PythonAnywhere จะเลิกใช้เมื่อหมดอายุ (2026-07)**

### 5.0 สถานะปัจจุบัน (สำคัญ — อ่านก่อน)
เจ้าของต้องการ **custom domain ของตัวเอง** ซึ่ง PythonAnywhere free tier ทำไม่ได้ (บังคับ
`username.pythonanywhere.com` เท่านั้น ต้องอัปเกรดเสียเงินถึงจะแม็พโดเมนได้) จึงย้ายไป
**Render.com** แทน (`render.yaml` ที่เคยเขียนไว้ตั้งแต่แรกแต่ไม่ได้ใช้ ถูกเอากลับมาใช้จริงแล้ว)
**Render ยืนยันแล้วว่า deploy สำเร็จและเป็นเว็บหลักตอนนี้** — PythonAnywhere จะถูกปล่อยให้
**หมดอายุไปเอง** (ไม่ต่ออายุ) เมื่อครบกำหนดเดือนถัดไป ไม่ใช่ปิดมือทันที

| | PythonAnywhere (legacy — จะหมดอายุ) | Render (หลัก — Live แล้ว) |
|---|---|---|
| สถานะ ณ commit `c70dfb6` | ✅ ยังออนไลน์อยู่ (เช็คแล้ว `/healthz` → 200) — **แต่จะไม่ต่ออายุ** ครั้งถัดไปที่ครบ 1 เดือน | ✅ **Live แล้ว** (เช็คแล้ว `/healthz` → 200) |
| URL | https://bunniee.pythonanywhere.com | **https://fieldnotes-pph8.onrender.com** |
| ข้อมูล (essay/รูป/about) | มีเนื้อหาจริงของเจ้าของอยู่ (Skardu essay ครบ + about ที่กรอกแล้ว) | ต้องเช็คกับเจ้าของว่าคีย์เนื้อหาจริงผ่าน `/admin` แล้วหรือยัง (ตอน deploy เสร็จใหม่ ๆ ยังเป็น DB เปล่า) |
| custom domain | ❌ ทำไม่ได้ (free tier) | ✅ ได้ (ต้องซื้อโดเมนก่อน — **ยังไม่ได้ซื้อ** ณ ตอนเขียนไฟล์นี้ ใช้ `.onrender.com` ไปก่อน) |

**⚠️ ชื่อ URL จริงไม่ตรงกับที่ตั้งใน `render.yaml`:** ตั้ง `name: fieldnotes` ไว้ แต่ชื่อนี้ชน
กับคนอื่นบน Render (ตามที่เตือนไว้ล่วงหน้าว่ามีโอกาสสูง เพราะเป็นชื่อสามัญ) → Render เติม
suffix `-pph8` ให้อัตโนมัติ กลายเป็น `fieldnotes-pph8.onrender.com` **ห้ามสมมติว่า URL =
`<name ใน render.yaml>.onrender.com` เป๊ะ ๆ เสมอไป — เช็ค URL จริงจาก Render dashboard
หรือถามเจ้าของทุกครั้ง**

**สิ่งที่ยังไม่เสร็จ (งานค้างของเจ้าของ ไม่ใช่บั๊ก):**
1. เช็คกับเจ้าของว่าตั้งรหัสผ่าน admin บน Render แล้วหรือยัง + คีย์เนื้อหาจริงผ่าน `/admin`
   (essay/about/gallery) ครบหรือยัง — ณ ตอนเขียนไฟล์นี้ยังไม่ยืนยัน
2. **ยังไม่ได้ซื้อโดเมน** — ใช้ `.onrender.com` ไปก่อน ซื้อทีหลังได้ไม่ต้อง deploy ใหม่
   (แค่ไปเพิ่มใน Render Settings → Custom Domains + ตั้ง DNS record ที่ registrar)
3. **PythonAnywhere จะหมดอายุเอง** — ไม่ต้องทำอะไรเพิ่ม แค่รู้ไว้ว่าจะหายไปเฉย ๆ เมื่อครบกำหนด
   (ไม่ใช่ "เว็บพัง" ถ้าเกิดขึ้น — เป็นแผนที่ตั้งใจ) ถ้าเจ้าของเปลี่ยนใจอยากต่ออายุ ต้องกดปุ่ม
   "Run until 1 month from today" ในหน้า Web ของ PythonAnywhere ก่อนวันหมดอายุ

**ถ้า session ในอนาคตต้องแก้บั๊ก "เว็บใช้ไม่ได้":** **Render (`fieldnotes-pph8.onrender.com`)
คือเว็บหลักที่ต้องดูก่อน** — PythonAnywhere ยังไม่ตายจนกว่าจะหมดอายุจริง แต่ไม่ใช่ที่ที่เจ้าของ
ดูแลต่อแล้ว

### 5.1 Render (deployment หลัก — **Live** ที่ https://fieldnotes-pph8.onrender.com)

Config ทั้งหมดอยู่ใน [`render.yaml`](render.yaml) แล้ว — deploy ผ่าน **Blueprint**
(Render dashboard → New + → Blueprint → เลือก repo) ไม่ต้องตั้งอะไรเพิ่มในหน้าเว็บ Render เอง

```yaml
# สรุปจาก render.yaml (อ่านไฟล์จริงเพื่อความชัวร์ ไฟล์นี้แก้ได้บ่อย)
name: fieldnotes              # ← ค่าที่ "ขอ" ไว้ แต่ URL จริงกลายเป็น fieldnotes-pph8
                               #   เพราะชื่อนี้ชนกับคนอื่นบน Render (ดูหมายเหตุด้านล่าง)
plan: starter                 # ต้องเป็น starter ขึ้นไป — "free" ไม่มี persistent disk
                               # (ไม่มี disk = app.db + uploads/ หายทุกครั้งที่ redeploy)
disk: mountPath /var/data, 5GB
env: FN_DB_PATH=/var/data/app.db, FN_UPLOAD_DIR=/var/data/uploads, FN_HTTPS=1
startCommand: "python seed.py; gunicorn app:app --workers 2 --bind 0.0.0.0:$PORT --timeout 120"
```

**กลไกสำคัญที่ต้องเข้าใจ:**
- **"Blueprint Name" ในหน้า deploy ของ Render ≠ ชื่อ URL** — Blueprint Name เป็นแค่ชื่อเรียก
  กลุ่ม services ใน dashboard เท่านั้น ชื่อ URL (`<name>.onrender.com`) มาจาก `name:` field
  ใน `render.yaml` (เคยทำให้เจ้าของสับสนตอน deploy จริง)
- **`name:` ใน render.yaml เป็นแค่คำขอ ไม่ใช่ผลลัพธ์ที่การันตี** — ถ้าชื่อซ้ำกับคนอื่นบน Render
  (เช่น `fieldnotes` เฉย ๆ) Render จะเติม suffix สุ่มให้เอง (ในเคสนี้ได้ `-pph8`) **URL จริง
  จึงอาจไม่ตรงกับที่เขียนใน render.yaml เป๊ะ ๆ — เช็คของจริงจาก Render dashboard หรือถาม
  เจ้าของเสมอ อย่าคำนวณ URL เอาเองจากไฟล์**
- **แก้ชื่อ URL:** แก้ `name:` ใน render.yaml → commit + push → กลับไปหน้า Render แล้ว
  **Manual sync** (หรือ push ใหม่จะ sync อัตโนมัติ) — แต่ผลลัพธ์อาจโดนเติม suffix อีกถ้าชื่อ
  ที่เลือกใหม่ยังซ้ำอยู่ — ห้ามลืมว่าถ้าไปแก้ชื่อใน Render Settings ตรง ๆ โดยไม่แก้
  render.yaml ด้วย ครั้งหน้าที่ sync จาก Blueprint อาจเปลี่ยนชื่อกลับไปเป็นค่าใน render.yaml
- **ประวัติชื่อ service** (เผื่อเจอ URL เก่าใน log/เอกสาร): `field-notes` (ค่าดั้งเดิมใน
  render.yaml ตั้งแต่ commit `86a7ac6`) → `sobanali-field-notes` (commit `6713709`)
  → `fieldnotes` (commit `9b2d252`) → **URL จริงที่ได้: `fieldnotes-pph8`** (ชนชื่อ, Render
  เติม suffix อัตโนมัติ)
- **`seed.py` รันทุกครั้งที่ start** แต่เป็น idempotent (ข้ามถ้ามีข้อมูลอยู่แล้ว) — ปลอดภัย
- **โค้ดไม่มี hardcode โดเมนไหนเลย** (ตรวจแล้ว: ไม่มี Referer/Origin check, sitemap/robots.txt
  ใช้ `request.url_root` แบบ dynamic) → ย้ายโดเมน/เปลี่ยนชื่อ service ได้โดยไม่ต้องแก้โค้ด `app.py`

**ทำไมไม่ copy DB จาก local ไป Render ตรง ๆ:** `data/`, `uploads/`, `*.db` ถูก `.gitignore`
**โดยตั้งใจ** (git ไม่เหมาะเก็บไบนารีขนาดใหญ่ + DB มี password hash ที่ไม่ควรอยู่ใน git history)
ทำได้จริงผ่าน Render Shell (`curl` ไฟล์ zip ลงมาที่ `/var/data/`) แต่เจ้าของเลือกคีย์ใหม่ผ่าน
`/admin` เอง (เนื้อหาจริงมีแค่ essay เดียว + gallery ไม่กี่รูป ไม่ได้เยอะมาก)

### 5.2 PythonAnywhere (legacy — ยังออนไลน์อยู่ แต่จะปล่อยให้หมดอายุ ไม่ต่ออายุแล้ว)

| ค่า | |
|---|---|
| Username | `bunniee` |
| URL | https://bunniee.pythonanywhere.com |
| โค้ด | `/home/bunniee/field-notes-website` |
| **ข้อมูล (สำคัญ)** | `/home/bunniee/field-notes-data/` → `app.db` + `uploads/` |
| virtualenv | `/home/bunniee/.virtualenvs/fieldnotes-venv` (Python 3.10) |
| Web app config | Manual configuration (ไม่ใช่ Flask wizard) |

#### WSGI file (ตั้งค่าไว้แล้ว)
```python
import sys, os
path = '/home/bunniee/field-notes-website'
if path not in sys.path:
    sys.path.insert(0, path)
os.environ['FN_DB_PATH']    = '/home/bunniee/field-notes-data/app.db'
os.environ['FN_UPLOAD_DIR'] = '/home/bunniee/field-notes-data/uploads'
os.environ['FN_HTTPS']      = '1'
from app import app as application
```

#### Static files mapping (ตั้งค่าไว้แล้ว)
| URL | Directory |
|---|---|
| `/static/` | `/home/bunniee/field-notes-website/static/` |
| `/uploads/` | `/home/bunniee/field-notes-data/uploads/` |

#### วิธี deploy โค้ดใหม่ (ถ้ายังใช้อยู่)
```bash
# ใน Bash console ของ PythonAnywhere
cd ~/field-notes-website && git pull
workon fieldnotes-venv && pip install -r requirements.txt   # ถ้า requirements เปลี่ยน
# → แล้วกดปุ่ม "Reload" ในหน้า Web
```
Migration ใน `db.py` รันอัตโนมัติตอน app boot **ไม่ต้องรันมือ**

#### ⚠️ ข้อจำกัด free tier ที่ต้องรู้ (ถ้ายังใช้อยู่)
- **ต้องกดปุ่ม "Run until 1 month from today" ในหน้า Web ทุกเดือน** ไม่งั้นเว็บถูกปิด
  (มีอีเมลเตือนล่วงหน้า 1 สัปดาห์)
- พื้นที่จำกัด ~512MB · ใช้โดเมนตัวเองไม่ได้ · outbound internet ถูกจำกัด (ไม่กระทบเว็บนี้)

---

## 6. รันบนเครื่อง (local dev)

**เครื่อง Mac ของเจ้าของ:** `/Users/sobanalishahzad/Desktop/claude /photo essay/project buit web/field-notes-cms`
(⚠️ path มีช่องว่างและช่องว่างท้ายคำว่า `claude ` — **ต้องใส่ quote เสมอ**)

```bash
python3 -m pip install --user -r requirements.txt
python3 seed.py          # ครั้งเดียว
./run.sh start           # → http://localhost:8000
./run.sh status | restart | stop | logs
```

- **ห้ามใช้ `python3 app.py` เป็นเว็บจริง** — dev server ตายเมื่อปิด terminal
  (เคยเป็นเหตุให้ "เว็บใช้ไม่ได้" มาแล้ว) · `run.sh` รัน gunicorn แบบ detached (PPID=1)
- **DB ของ local กับ production เป็นคนละไฟล์กันโดยสิ้นเชิง** — เนื้อหาที่แก้ผ่าน `/admin`
  บนเครื่อง **ไม่ไป** production (เนื้อหาไม่ได้อยู่ใน git โดยตั้งใจ)

### สภาพแวดล้อมเครื่องเจ้าของ (ข้อจำกัดที่ต้องรู้)
- Python 3.9 (`/usr/bin/python3`) · **ไม่มี Node.js · ไม่มี Homebrew · ไม่มี `gh` CLI**
- git ใช้ได้ + token เก็บใน macOS Keychain แล้ว (`git push` ได้เลยไม่ต้องถามรหัส)

---

## 7. ปัญหาที่เคยเจอ + วิธีแก้ (อ่านก่อนแก้บั๊ก — ประหยัดเวลามาก)

### 7.1 บั๊ก/ข้อจำกัดของสภาพแวดล้อม
| ปัญหา | สาเหตุ + วิธีแก้ |
|---|---|
| `AttributeError: module 'hashlib' has no attribute 'scrypt'` | Python ของ Apple CLT ไม่มี scrypt ที่ werkzeug ใช้ default → **ต้องระบุ `generate_password_hash(method="pbkdf2:sha256")` เสมอ** |
| `PermissionError: Operation not permitted` ตอนอ่าน template | macOS TCC บล็อกโปรเซสที่ agent spawn ให้อ่านไฟล์ใน `~/Desktop` → preview tool รันแอปจาก Desktop ไม่ได้ ต้อง rsync ไป `/tmp` แล้วรันจากที่นั่น (หรือใช้ `run.sh` ผ่าน Bash ปกติซึ่งไม่โดนบล็อก) |
| "เว็บใช้ไม่ได้" (เกิด 2 ครั้ง) | ไม่มีอะไรรันเว็บอยู่ (dev server ตายไปแล้ว) → เช็ค `./run.sh status` ก่อนเสมอ อย่าเดาว่าเป็นบั๊กโค้ด |
| `git push` ขึ้น `could not read Username` | terminal non-interactive → ใช้ PAT + `git credential approve` เก็บใน Keychain (ทำไปแล้ว) |

### 7.2 กับดักตอนเขียน/ทดสอบโค้ด
| กับดัก | ต้องทำอย่างไร |
|---|---|
| **curl ทดสอบ admin** | ต้องใส่ `-c` (cookie jar) **ทุก request** — login จะ rotate session ทำให้ CSRF token เปลี่ยน · **ห้ามใช้ `-L`** (มัน replay POST ไปยัง redirect target → เกิด 400/404 สับสน) |
| **Flask session ที่เป็น dict ซ้อน** | ต้อง **reassign** กลับ (`session["pending"] = tokens`) ไม่งั้น Flask ไม่รู้ว่ามีการเปลี่ยนแปลง |
| **`hmac.compare_digest`** | โยน TypeError ถ้าได้ str ที่ไม่ใช่ ASCII → ต้อง `.encode()` เป็น bytes ก่อน (แก้แล้ว) |
| **ทดสอบ analytics ด้วย curl** | UA ของ curl ถูกกรองเป็น bot → จะไม่ถูกนับ ต้องปลอม UA เป็น browser |
| **screenshot ของ browser preview** | มัน re-render/reload → **lightbox ที่เปิดด้วย JS จะหาย** และ scroll position ไม่นิ่ง → ยืนยันด้วย `javascript_tool` (computed styles / bounding boxes) แทน |
| **เพิ่มฟอร์ม admin ใหม่** | ต้องใส่ csrf_token hidden input ไม่งั้น 400 |
| **`window.scrollTo()` ใน browser preview tool ไม่น่าเชื่อถือ** | บางครั้ง scroll ไม่ขยับเลย (`scrollY` ยังเป็น 0) หรือ `getBoundingClientRect()` อ่านค่าตำแหน่งเก่าทันทีหลัง scroll (race condition กับ reflow) → เจอตอนไล่เช็ค responsive/reveal-animation ที่ tablet/desktop **สรุป: นี่คือ tooling quirk ไม่ใช่บั๊กเว็บ** — ยืนยันด้วย `computer{action:"scroll"}` (การ scroll จริงแบบ user) หรือรอ 1-2 วิ (`sleep`) ก่อนอ่านค่า/screenshot ซ้ำ |
| **`IntersectionObserver` (.reveal fade-in) ไม่ทำงานกับ scroll แบบ JS jump** | element ที่ผ่านไปด้วย `scrollTo()` แบบทันที (ไม่ใช่ scroll จริงทีละนิด) บางครั้ง IO ไม่ fire → เห็นเนื้อหาเป็นสีจาง (opacity 0) ในสกรีนช็อต ทั้งที่โค้ดไม่มีบั๊ก (ยืนยันด้วย `computer{action:"scroll"}` จริงแล้วทำงานถูกต้อง) — อย่าตกใจว่าเป็นบั๊กถ้าเจอหน้าจอง่วง ๆ ระหว่างทดสอบด้วย JS scroll |

### 7.3 บทเรียนเรื่องรูปภาพ (สำคัญมาก)
**ห้ามเชื่อการ map ชื่อไฟล์รูปจากเอกสารเก่าเด็ดขาด** — เคยพบว่า mapping ผิด **6 plates**
(หน้า essay แสดงรูปสะพานซ้ำ/รถจี๊ปแทนพ่อครัว ฯลฯ) ต้อง **ตรวจเนื้อหาภาพด้วยตาเสมอ**
(สร้าง thumbnail แล้วดู) ก่อนจับคู่รูปกับ caption

รูปต้นฉบับทั้งหมด (106 ไฟล์) อยู่ที่ `photo essay/` และ `project buit web/photo essay/` บนเครื่องเจ้าของ
(สองโฟลเดอร์นี้ไฟล์เหมือนกันเป๊ะ)

### 7.4 Performance/caching (ตรวจ + แก้ 2026-07 — เจ้าของกังวลเรื่องผู้ใช้เน็ตช้า)

**สิ่งที่แก้แล้ว:**
- **`loading="lazy"` หายไปจาก 2 จุด** ใน `landing.html`: รูป featured essay + การ์ด
  "More essays" ทั้ง 3 ใบ — โหลดทันทีตั้งแต่เปิดหน้าทั้งที่อยู่ใต้ fold ตอนนี้เพิ่ม
  `loading="lazy"` แล้ว ให้เหมือนกับ gallery/about/plates ที่มีอยู่แล้ว
- **`Cache-Control: no-cache` บนรูปทุกรูป** (ทั้ง `/static/` และ `/uploads/`) — เป็นค่า
  default ของ Flask เมื่อไม่ได้ตั้ง `SEND_FILE_MAX_AGE_DEFAULT` ทำให้ทุก visit ต้อง
  revalidate กับ server ก่อนใช้ cache (round-trip เพิ่มทุกครั้ง) แก้แล้วใน `app.py`:
  - `/static/*` → `SEND_FILE_MAX_AGE_DEFAULT = 86400` (1 วัน — ไฟล์ default อาจเปลี่ยนผ่าน git)
  - `/uploads/*` → `max_age=31536000` + `Cache-Control: public, max-age=31536000, immutable`
    (ปลอดภัยเพราะไฟล์อัปโหลดใช้ชื่อ UUID **ที่ไม่เคยถูกเขียนทับ** — อัปโหลดใหม่ = ชื่อไฟล์ใหม่
    เสมอ ดู `images.py`)
- **essay ที่ไม่มี hero_image โชว์ broken-image icon** — ไม่มีการบังคับต้องมีรูปก่อน publish
  (`essay_publish()` ใน app.py ไม่เช็ค) แก้โดยเช็ค `{% if e.hero_image %}` ก่อน render
  `<img>` ใน `landing.html`/`essays.html`, ไม่มีรูป → placeholder สีเบจแทน

**สิ่งที่ยังไม่แก้ (คุยกับเจ้าของแล้ว ตัดสินใจเลื่อนไปทำทีหลัง):**
- **ไม่มี thumbnail แยกขนาดสำหรับการ์ด** — การ์ด "More essays"/`/essays` ใช้ไฟล์ hero
  เดียวกับที่โชว์เต็มจอในหน้า essay (`images.py` role `"hero"` = max 2200px, ~700KB) แต่
  แสดงในกล่องเล็กแค่ ~380×280px ถ้าจะทำ: เพิ่ม role ใหม่ใน `images.py` (เช่น `"thumb"`
  ~600px), เพิ่มคอลัมน์เก็บ path แยกใน `essays` (schema.sql + migration), แก้
  `essay_hero()` ให้ generate ทั้งสองขนาดตอนอัปโหลด, แล้ว regenerate รูปเก่าที่มีอยู่แล้ว
  — งานเปลี่ยน schema จึงเลื่อนไว้เป็น future feature (ดู §8)

---

## 8. งานค้างเร่งด่วน (ทำก่อนอย่างอื่น — ดู §5.0 ด้วย)

~~1. ยืนยัน Render deploy สำเร็จ~~ ✅ **เสร็จแล้ว** — Live ที่ `fieldnotes-pph8.onrender.com`
   (เช็คแล้วจริง `/healthz` → 200 ตอนอัปเดตไฟล์นี้ครั้งล่าสุด)
2. **เช็คกับเจ้าของว่าตั้งรหัสผ่าน admin + คีย์เนื้อหาจริงผ่าน `/admin`** บน Render
   (essay Skardu + plates, about bio, LinkedIn/email, gallery) ครบหรือยัง — ยังไม่ยืนยัน
   ณ ตอนเขียนไฟล์นี้
3. **ซื้อโดเมน + ผูกกับ Render** (Settings → Custom Domains + DNS record ที่ registrar)
   — ยังไม่ได้ซื้อ ใช้ `.onrender.com` ไปก่อน
~~4. ตัดสินใจอนาคตของ PythonAnywhere~~ ✅ **ตัดสินใจแล้ว** — ปล่อยให้หมดอายุไปเอง ไม่ต่ออายุ
   ไม่ต้องทำอะไรเพิ่ม (ดู §5.0/§5.2)
5. **(เสนอไว้ ยังไม่ได้ทำ) responsive thumbnail สำหรับการ์ด essay** — ดู §7.4 ท้ายสุด
   สำหรับรายละเอียดว่าต้องแก้อะไรบ้าง (schema + `images.py` + regenerate รูปเก่า)

---

## 9. Feature ในอนาคต (แผนระยะยาว — คุยกับเจ้าของไว้ตั้งแต่ก่อนหน้านี้)

เจ้าของต้องการขยายจาก *photo-essay journal* → *personal scholarly + creative portfolio*
โดยเพิ่ม **บทความ (articles)** และ **เอกสารทางวิชาการ (academic papers)**

### แนวทางที่วางไว้: เพิ่มคอลัมน์ `kind` ใน `essays` (ไม่สร้างระบบใหม่แยก)
| kind | สถานะ | หน้าตา |
|---|---|---|
| `photo_essay` | ✅ มีแล้ว | dark scrollytelling + plates |
| `article` | 📋 วางแผน | text-first, Markdown |
| `paper` | 📋 วางแผน | metadata วิชาการ + PDF + citation |

**ข้อดี:** reuse ได้ทั้ง changeset engine, slug, analytics, SEO, admin CRUD — เปลี่ยนแค่
ฟอร์มใน admin + template ตอนเรนเดอร์ · migration เป็น additive (essay เดิม → `kind='photo_essay'`)

### เฟสที่วางไว้
- **เฟส 0:** เพิ่ม `kind` + generalize dashboard/nav/ปุ่มสร้างใหม่
- **เฟส 1 — บทความ:** Markdown editor (ต้องเพิ่ม lib `markdown` + `bleach` sanitize) ·
  หน้า `/writing` · reading time · สารบัญอัตโนมัติ · แท็ก
- **เฟส 2 — เอกสารวิชาการ:** authors/abstract/keywords/DOI · **อัปโหลด PDF** (ระบบยังรับแค่รูป
  ต้องขยาย) · citation export (BibTeX/RIS) · **Google Scholar meta tags** · หน้า `/research`
- **เฟส 3:** search (SQLite **FTS5** — มีในตัว ไม่ต้องลง service) · RSS feed ·
  About → CV เต็มรูปแบบ · Schema.org structured data

### สิ่งที่คงเดิมไม่ต้องแตะ
photo essay engine · analytics · security · changeset/preview · archive gallery

### จุดที่เจ้าของต้องตัดสินใจก่อนเริ่ม
1. บทความอยากได้ scrollytelling สวย ๆ หรืออ่านล้วนแบบ Medium?
2. ระดับวิชาการ — แค่แปะ PDF ให้โหลด หรือต้อง citation export + Scholar indexing เต็มรูปแบบ?
3. รองรับผู้ร่วมเขียน (co-authors) ไหม?

---

## 10. Convention & รสนิยมของเจ้าของ

- **เนื้อหาเว็บเป็นอังกฤษล้วน** (ทั้ง public + admin UI) · **เอกสาร/README/คุยกับเจ้าของเป็นไทย**
- **ห้ามทำให้สงครามดูสวยงาม** — thesis ของ essay Skardu คือ *ความปกติภายใต้แรงกดดัน*
  (normalcy under pressure) เขียน copy ให้สงบ ไม่ดราม่า
- ดีไซน์: warm editorial — cream `#faf7f2` / ink `#1a1714` / accent ส้มอิฐ `#b5542d`
  (dark theme ใช้ `#12100d` + accent `#e8a87b`) · ฟอนต์ **Fraunces** (serif) + **Inter** (sans)
- เจ้าของเซ็นชื่อ **"BUN"**
- ทำงานแบบ: **ตรวจจริง ไม่เดา** — ทดสอบด้วย curl/browser จริงเสมอ แล้วรายงานผลตามจริง
- **mobile-first UX สำคัญมาก** — เจ้าของขอให้ตรวจทุกอุปกรณ์ (mobile/tablet/desktop) และเน็ตช้า
  โดยเฉพาะ (2026-07) → เวลาเพิ่มฟีเจอร์ใหม่ ให้ทดสอบ responsive + ผลกระทบต่อขนาดหน้า/รูปด้วยเสมอ
  ไม่ใช่แค่ desktop
- **ปุ่ม/ลิงก์ติดต่อ (contact) ใช้ pill-shape ขอบบาง** ตาม `.contact-link` ใน `landing.html`
  (border 1px, border-radius 999px, hover เปลี่ยนสี accent) — ใช้ pattern เดียวกันถ้าจะเพิ่ม
  ลิงก์โซเชียลอื่นในอนาคต (Instagram ก็ใช้ style คล้ายกันใน footer)
- **placeholder เมื่อไม่มีรูป** ใช้สีเบจ `#e3ddd2` (การ์ด) แทน broken-image icon เสมอ
  ไม่ใช่ alt text เปล่า ๆ

---

## 11. Checklist ก่อน commit

- [ ] `python3 -m py_compile app.py db.py images.py analytics.py seed.py`
- [ ] Jinja templates parse ได้ (`jinja2.Environment().parse(...)`)
- [ ] `./run.sh restart` แล้ว smoke test: `/`, `/essays`, `/essay/skardu`, `/admin/login`, `/healthz`, `/sitemap.xml`
- [ ] ฟอร์ม admin ใหม่ทุกอันมี `csrf_token`
- [ ] ถ้าเพิ่มคอลัมน์ DB → เขียนทั้งใน `schema.sql` **และ** migration ใน `db.py`
  (key ใหม่ใน `site_content`/`SITE_DEFAULTS` **ไม่ต้อง** — ดู §3)
- [ ] ล้างข้อมูลทดสอบ (`DELETE FROM settings WHERE key='admin_password'` ให้เจ้าของตั้งเอง)
- [ ] `git status` — ต้องไม่มี `data/`, `uploads/`, `logs/`, `run/` หลุดเข้า repo
- [ ] **ถ้าแก้ `render.yaml`** — push แล้วเช็คใน Render dashboard ว่า sync ไปแล้วจริง
  (Manual sync หรือรอ auto-sync) ก่อนบอกเจ้าของว่า "เสร็จแล้ว" — อย่าสมมติว่า push = deploy แล้ว
