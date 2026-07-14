# Field Notes CMS — Handoff for Claude Code

> อ่านไฟล์นี้ให้จบก่อนแตะอะไรก็ตาม เอกสารนี้เขียนให้ Claude Code session ในอนาคต
> เข้าใจโปรเจกต์นี้ได้ครบโดยไม่ต้องถามเจ้าของซ้ำ
>
> **Owner:** BUN (mrsobanali786@gmail.com) — สื่อสารภาษาไทย
> **Live site:** https://bunniee.pythonanywhere.com
> **GitHub:** https://github.com/mamamiya2114/field-notes-website
> **Last updated:** 2026-07 (commit `a1af01d`)

---

## 1. โปรเจกต์นี้คืออะไร

**Field Notes** — เว็บ photo-essay ส่วนตัวของ BUN ช่างภาพ/นักวิจัย ที่มีระบบหลังบ้าน (CMS)
ให้เจ้าของลงงานเองได้โดยไม่ต้องแตะโค้ด

- **หน้าสาธารณะ:** landing (editorial light theme) + หน้า essay (dark scrollytelling)
- **หลังบ้าน `/admin`:** สร้าง/แก้ essay, แก้เนื้อหาหน้าแรก, จัดการ archive gallery, ดูสถิติ
- **เนื้อหาหลักปัจจุบัน:** photo essay 1 เรื่อง — *"Life that does not stop, even with war
  within arm's reach"* (Skardu, Pakistan, พฤษภาคม 2025) 17 ภาพ + 1 interlude ถ่ายช่วง
  ความขัดแย้งอินเดีย–ปากีสถานปะทุ

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
├── Procfile / render.yaml    ← สำหรับ Render (ไม่ได้ใช้แล้ว — ดู §5)
│
├── templates/
│   ├── landing.html          ← หน้าแรก (hero, featured, archive gallery, about, footer)
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

## 5. Deployment — PythonAnywhere (production ปัจจุบัน)

**เลือก PythonAnywhere เพราะเจ้าของต้องการฟรี** (Render ต้องจ่ายเพื่อได้ persistent disk —
free tier ของ Render ไม่มีดิสก์ถาวร ข้อมูลจะหายทุก deploy) · `render.yaml`/`Procfile` ยังอยู่ใน
repo แต่ **ไม่ได้ใช้แล้ว**

| ค่า | |
|---|---|
| Username | `bunniee` |
| URL | https://bunniee.pythonanywhere.com |
| โค้ด | `/home/bunniee/field-notes-website` |
| **ข้อมูล (สำคัญ)** | `/home/bunniee/field-notes-data/` → `app.db` + `uploads/` |
| virtualenv | `/home/bunniee/.virtualenvs/fieldnotes-venv` (Python 3.10) |
| Web app config | Manual configuration (ไม่ใช่ Flask wizard) |

### WSGI file (ตั้งค่าไว้แล้ว)
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

### Static files mapping (ตั้งค่าไว้แล้ว)
| URL | Directory |
|---|---|
| `/static/` | `/home/bunniee/field-notes-website/static/` |
| `/uploads/` | `/home/bunniee/field-notes-data/uploads/` |

### วิธี deploy โค้ดใหม่
```bash
# ใน Bash console ของ PythonAnywhere
cd ~/field-notes-website && git pull
workon fieldnotes-venv && pip install -r requirements.txt   # ถ้า requirements เปลี่ยน
# → แล้วกดปุ่ม "Reload" ในหน้า Web
```
Migration ใน `db.py` รันอัตโนมัติตอน app boot **ไม่ต้องรันมือ**

### ⚠️ ข้อจำกัด free tier ที่ต้องรู้
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

### 7.3 บทเรียนเรื่องรูปภาพ (สำคัญมาก)
**ห้ามเชื่อการ map ชื่อไฟล์รูปจากเอกสารเก่าเด็ดขาด** — เคยพบว่า mapping ผิด **6 plates**
(หน้า essay แสดงรูปสะพานซ้ำ/รถจี๊ปแทนพ่อครัว ฯลฯ) ต้อง **ตรวจเนื้อหาภาพด้วยตาเสมอ**
(สร้าง thumbnail แล้วดู) ก่อนจับคู่รูปกับ caption

รูปต้นฉบับทั้งหมด (106 ไฟล์) อยู่ที่ `photo essay/` และ `project buit web/photo essay/` บนเครื่องเจ้าของ
(สองโฟลเดอร์นี้ไฟล์เหมือนกันเป๊ะ)

---

## 8. Feature ในอนาคต (แผนที่คุยกับเจ้าของไว้แล้ว)

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

## 9. Convention & รสนิยมของเจ้าของ

- **เนื้อหาเว็บเป็นอังกฤษล้วน** (ทั้ง public + admin UI) · **เอกสาร/README/คุยกับเจ้าของเป็นไทย**
- **ห้ามทำให้สงครามดูสวยงาม** — thesis ของ essay Skardu คือ *ความปกติภายใต้แรงกดดัน*
  (normalcy under pressure) เขียน copy ให้สงบ ไม่ดราม่า
- ดีไซน์: warm editorial — cream `#faf7f2` / ink `#1a1714` / accent ส้มอิฐ `#b5542d`
  (dark theme ใช้ `#12100d` + accent `#e8a87b`) · ฟอนต์ **Fraunces** (serif) + **Inter** (sans)
- เจ้าของเซ็นชื่อ **"BUN"**
- ทำงานแบบ: **ตรวจจริง ไม่เดา** — ทดสอบด้วย curl/browser จริงเสมอ แล้วรายงานผลตามจริง

---

## 10. Checklist ก่อน commit

- [ ] `python3 -m py_compile app.py db.py images.py analytics.py seed.py`
- [ ] Jinja templates parse ได้ (`jinja2.Environment().parse(...)`)
- [ ] `./run.sh restart` แล้ว smoke test: `/`, `/essay/skardu`, `/admin/login`, `/healthz`, `/sitemap.xml`
- [ ] ฟอร์ม admin ใหม่ทุกอันมี `csrf_token`
- [ ] ถ้าเพิ่มคอลัมน์ DB → เขียนทั้งใน `schema.sql` **และ** migration ใน `db.py`
- [ ] ล้างข้อมูลทดสอบ (`DELETE FROM settings WHERE key='admin_password'` ให้เจ้าของตั้งเอง)
- [ ] `git status` — ต้องไม่มี `data/`, `uploads/`, `logs/`, `run/` หลุดเข้า repo
