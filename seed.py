"""Seed the database with the existing Skardu essay so it becomes editable and
tracked through the CMS. Idempotent: skips if an essay with the slug exists.

Run once after install:  python3 seed.py
Source images are read from ../field-notes/essay/images and re-optimized into
/uploads via images.import_from_path.
"""
import os
import sqlite3

import db
import images

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Prefer the bundled seed_images/ (ships with this repo, works on any host);
# fall back to the legacy static-site folder when running from the full project.
_CANDIDATES = [
    os.path.join(BASE_DIR, "seed_images"),
    os.path.normpath(os.path.join(BASE_DIR, "..", "field-notes", "essay", "images")),
]
SRC_IMG = next((p for p in _CANDIDATES if os.path.isdir(p)), _CANDIDATES[0])

SLUG = "skardu"

ESSAY = dict(
    slug=SLUG,
    title_th="ชีวิตที่ไม่หยุด\nแม้สงครามใกล้แค่เอื้อม",
    title_en="Life that does not stop, even with war within arm's reach.",
    kicker="Photo Essay № 01 — Skardu, Pakistan",
    location="Skardu, Pakistan",
    date_text="พฤษภาคม 2568",
    summary_en="Life that does not stop, even with war within arm's reach — Skardu, "
               "Pakistan, May 2025. Eighteen photographs of ordinary life continuing "
               "quietly beside a military airbase, as conflict flares in Kashmir.",
    lede="ท่ามกลางความขัดแย้งที่รุนแรงขึ้นระหว่างสองประเทศในเอเชียใต้ ปากีสถานและอินเดีย ช่วงเดือนพฤษภาคม 2568 ที่ผ่านมา เมืองเล็ก ๆ ที่เป็นจุดยุทธศาสตร์ทางการทหารสำคัญอย่าง Skardu ประเทศปากีสถาน ผู้คนที่นี่ดำเนินชีวิตอย่างเงียบสงบ แม้จะอยู่ใกล้ฐานทัพหลักในการปฏิบัติการทางอากาศ ที่ใช้ส่งกำลังรบไปยังพื้นที่ความขัดแย้งในเขตแคชเมียร์\n\n"
         "พวกเขายังคงทำมาหากิน เลี้ยงสัตว์ ค้าขาย ในแต่ละครอบครัว พ่อแม่ยังคงทำอาหาร เด็ก ๆ ยังคงเดินไปโรงเรียน ราวกับว่าความขัดแย้งนี้ไม่มีอยู่จริง ภาพถ่ายเหล่านี้จึงไม่เพียงสะท้อน “วิถีชีวิต” แต่ยังเป็นเครื่องยืนยันถึงสภาวะความปกติท่ามกลางความไม่แน่นอน",
    outro="เมื่อโลกเต็มไปด้วยความขัดแย้ง เราอาจลืมไปว่า “ผู้คนธรรมดา” ต่างหากคือกลุ่มที่ต้องใช้ชีวิตต่อไปท่ามกลางแรงกดดัน ภาพเหล่านี้ไม่ได้พยายามเสนอความสวยงามของสงคราม แต่คือบทพิสูจน์ว่าความปกติ ความรัก และความพยายามของผู้คน ยังคงเป็นพลังที่แข็งแกร่งกว่าเสียงปืนและความขัดแย้งใด ๆ",
    signature="BUN",
)

# (source filename, layout, caption_th, caption_en, alt)
PLATES = [
    ("p01-bridge.jpg", "full",
     "“แม้สะพานจะเก่าและสงครามจะใกล้ แต่ความรักของครอบครัวยังคงอยู่อย่างมั่นคง”",
     "The bridge is old. The war is close. The child does not let go of either hand.",
     "ครอบครัวเดินข้ามสะพานแขวนเก่า"),
    ("p02-family.jpg", "normal",
     "“ไม่มีใครรู้ว่าพรุ่งนี้จะเกิดอะไรขึ้น แต่วันนี้ พ่อ แม่ และลูก ยังคงขับเคลื่อนไปด้วยกัน”",
     "", "พ่อแม่ลูกบนมอเตอร์ไซค์"),
    ("p03-dance.jpg", "normal",
     "“แม้ฟ้าจะปกคลุมด้วยความไม่แน่นอน เด็กน้อยยังคงเต้นระบำขณะที่พ่อแม่ถ่ายรูป — ความสุขเล็ก ๆ ที่ไม่ยอมให้สงครามพรากไปได้”",
     "", "เด็กน้อยเต้นระบำในศาลา"),
    ("p04-shops.jpg", "normal",
     "“ถึงบางร้านค้าจะปิดลง ทว่าโลกของเด็ก ๆ ยังเปิดกว้างให้วิ่งเล่น”",
     "", "เด็ก ๆ วิ่งเล่นหน้าร้านที่ปิด"),
    ("p05-school.jpg", "normal",
     "“ในกระเป๋าใบเล็กของเด็กหญิง มีทั้งหนังสือเรียน และความฝัน — ไม่มีใครสามารถทิ้งระเบิดใส่สิ่งเหล่านี้ได้”",
     "", "เด็กนักเรียนหญิงสะพายกระเป๋าเดินไปโรงเรียน"),
    ("p06-load.jpg", "full",
     "“แรงเล็ก ๆ แต่เต็มไปด้วยความรับผิดชอบที่เกินวัย”",
     "Small in frame. Immeasurable in load. This is the labour that development economists cannot find in their datasets.",
     "ร่างเล็ก ๆ แบกฟ่อนกิ่งไม้บนถนนภูเขา"),
    ("__interlude__", "interlude",
     "ในวันที่เมืองจดจ่ออยู่บนฟ้า ชีวิตใต้เงาภูเขากลับยังคงสงบนิ่งและเรียบง่ายในทุกจังหวะที่ก้าวเดิน",
     "While the world above negotiates chaos, the valley keeps its own time.\nThe valley has its own calendar. It does not observe the news cycle.", ""),
    ("p07-honey.jpg", "normal",
     "“ขณะที่โลกภายนอกร้อนระอุด้วยความตึงเครียด บ่ายวันธรรมดาที่แผงน้ำผึ้งและผลไม้ยังคงสงบนิ่งและอบอวลด้วยความหวาน”",
     "", "แผงขายน้ำผึ้งและผลไม้"),
    ("p08-walk.jpg", "full",
     "ในวันที่เมืองจดจ่ออยู่บนฟ้า ชีวิตใต้เงาภูเขากลับยังคงสงบนิ่งและเรียบง่ายในทุกจังหวะที่ก้าวเดิน",
     "On the day the city fixes its gaze upon the sky, life beneath the shadow of the mountain remains still and simple in every step forward.",
     "แม่ลูกเดินบนทางใต้เงาภูเขา"),
    ("p09-garden.jpg", "normal",
     "“แม้โลกจะสั่นไหว บ้านหลังนี้ยังยืนหยัดอยู่อย่างเงียบ ๆ พร้อมแปลงผักที่เติบโตไปตามฤดูกาล ไม่ใช่ตามสงคราม”",
     "", "บ้านกับแปลงผักใต้ร่มไม้"),
    ("p10-market.jpg", "normal",
     "“ในช่วงเวลาที่สงครามใกล้เข้ามา บทสนทนาในตลาดคือหลักฐานของความปกติสุขที่ยังคงมีอยู่”",
     "", "บทสนทนาในตลาด"),
    ("p11-kebab.jpg", "normal",
     "“ในวันที่โลกภายนอกกำลังเดือดดาล พ่อค้ายังคงง่วนอยู่กับเตาและลูกค้า — ไม่ใช่เพราะไม่รู้ว่าเกิดอะไรขึ้น แต่เพราะรู้ว่าใคร ๆ ก็ยังต้องกิน”",
     "", "พ่อค้าที่แผงอาหาร"),
    ("p12-cobbler.jpg", "normal",
     "“สงครามอาจเปลี่ยนแปลงแผนยุทธศาสตร์ แต่ฝีมือช่างซ่อมรองเท้ายังซื่อตรงเหมือนทุกวัน”",
     "", "ช่างซ่อมรองเท้าหน้าร้าน"),
    ("p13-cook.jpg", "normal",
     "“ในขณะที่เครื่องบินรบกำลังทะยานขึ้นจากเมืองนี้ พ่อบ้านยังคงยืนหน้าเตา ปรุงอาหารให้ครอบครัว”",
     "", "พ่อบ้านยืนปรุงอาหารหน้าเตา"),
    ("p14-snack.jpg", "normal",
     "“แม้เสียงปืนดังอยู่ไม่ไกลนัก แต่มุมหนึ่งของร้านค้า ผู้ใหญ่กำลังโอภาปราศรัยกันและกัน และเด็กหญิงกำลังเลือกขนม… สภาวะนี้ปกติมาก”",
     "", "เด็กหญิงเลือกขนมที่ร้านค้า"),
    ("p15-board.jpg", "full",
     "“เครื่องบินรบทะยานขึ้นสู่ท้องฟ้าเพื่อภารกิจรบ ด้านล่างเที่ยวบินของผู้คนถูกหยุดชั่วคราว — ไม่มีเสียงไซเรน ไม่มีข่าวใหญ่ แต่ความกลัวซึมผ่านตารางบิน”",
     "Fear does not announce itself. It updates silently — column by column — under the word Delayed.",
     "จอตารางบินแสดงเที่ยวบินล่าช้า"),
    ("p16-gaze.jpg", "normal",
     "แม้ฉากรอบกายจะดูนิ่งเฉย แต่ในแววตาและท่าทางของเด็กน้อย กลับสะท้อนถึงบางสิ่งที่กำลังสั่นคลอนอย่างเงียบเชียบ",
     "", "แววตาของเด็ก ๆ บนรถพ่วง"),
    ("p17-town.jpg", "full",
     "“เมืองเล็ก ๆ ที่เป็นจุดยุทธศาสตร์ของชาติ แต่เต็มไปด้วยผู้คนธรรมดา ที่ไม่ยอมแพ้ต่อโลกที่แปรผัน”",
     "", "ถนนสายหลักของเมือง Skardu"),
]

HERO_SRC = "p00-hero.jpg"


def main():
    db.init_db()
    # No source images (e.g. deployed repo contains only field-notes-cms/) →
    # nothing to import. Exit cleanly so server start is never blocked.
    if not os.path.isdir(SRC_IMG):
        print(f"seed: source images not found at {SRC_IMG} — skipping (nothing to do)")
        return
    conn = sqlite3.connect(db.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        if conn.execute("SELECT 1 FROM essays WHERE slug=?", (SLUG,)).fetchone():
            print(f"essay '{SLUG}' already exists — skipping seed")
            return

        cur = conn.execute(
            "INSERT INTO essays(slug,title_th,title_en,kicker,location,date_text,"
            "summary_en,lede,outro,signature,status,published_at) "
            "VALUES(:slug,:title_th,:title_en,:kicker,:location,:date_text,"
            ":summary_en,:lede,:outro,:signature,'published',datetime('now'))",
            ESSAY)
        eid = cur.lastrowid

        hero_rel = images.import_from_path(
            os.path.join(SRC_IMG, HERO_SRC), eid, role="hero", name="hero.jpg")
        conn.execute("UPDATE essays SET hero_image=? WHERE id=?", (hero_rel, eid))

        pos = 0
        for fname, layout, th, en, alt in PLATES:
            pos += 1
            if layout == "interlude":
                conn.execute(
                    "INSERT INTO plates(essay_id,position,kind,image,layout,caption_th,caption_en,alt)"
                    " VALUES(?,?,?,?,?,?,?,?)",
                    (eid, pos, "interlude", "", "normal", th, en, alt))
            else:
                rel = images.import_from_path(
                    os.path.join(SRC_IMG, fname), eid, role="plate",
                    name=fname.replace("p", "plate", 1))
                conn.execute(
                    "INSERT INTO plates(essay_id,position,kind,image,layout,caption_th,caption_en,alt)"
                    " VALUES(?,?,?,?,?,?,?,?)",
                    (eid, pos, "photo", rel, layout, th, en, alt))
        conn.commit()
        print(f"seeded essay '{SLUG}' (id={eid}) with {len(PLATES)} plates + hero")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
