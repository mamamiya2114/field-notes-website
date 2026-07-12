"""Seed the database with the Skardu essay so a fresh install starts with real
content. Idempotent: skips if an essay with the slug exists, and skips cleanly
when the bundled source images are missing.

Run once after install:  python3 seed.py
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
    title="Life that does not stop,\neven with war within arm's reach",
    kicker="Photo Essay № 01 — Skardu, Pakistan",
    location="Skardu, Pakistan",
    date_text="May 2025",
    summary="Skardu, Pakistan, May 2025. Eighteen photographs of ordinary life "
            "continuing quietly beside a military airbase, as conflict flares "
            "in Kashmir.",
    lede="In May 2025, as the conflict between Pakistan and India escalated "
         "sharply, life in Skardu — a small town of real military consequence — "
         "went on quietly. People here continued their days beside a key "
         "airbase, one used to send fighter aircraft toward the contested "
         "skies of Kashmir.\n\n"
         "They kept earning their living: herding, trading. In every family, "
         "parents still cooked and children still walked to school, as if the "
         "conflict did not exist. These photographs are not only a record of "
         "daily life — they are evidence of ordinariness holding its ground "
         "amid uncertainty.",
    outro="In a world crowded with conflict, we forget that it is ordinary "
          "people who must keep living under its weight. These pictures do not "
          "try to make war beautiful. They are proof that normalcy, love, and "
          "the quiet effort of ordinary people remain stronger than gunfire "
          "and any conflict.",
    signature="BUN",
)

# (source filename, layout, caption, alt)
PLATES = [
    ("p01-bridge.jpg", "full",
     "The bridge is old. The war is close. The child does not let go of either hand.",
     "A family crossing an old suspension bridge"),
    ("p02-family.jpg", "normal",
     "No one knows what tomorrow will bring. Today, father, mother and child still move forward together.",
     "A family riding together on a motorbike"),
    ("p03-dance.jpg", "normal",
     "Under an uncertain sky, a little girl dances while her parents take pictures — a small happiness the war cannot take away.",
     "A child dancing in a pavilion"),
    ("p04-shops.jpg", "normal",
     "Some shops have closed, but the world of children stays wide open for play.",
     "Children playing in front of shuttered shops"),
    ("p05-school.jpg", "normal",
     "In a schoolgirl's small bag there are textbooks and dreams — no one can drop a bomb on those.",
     "Schoolgirls with backpacks walking to school"),
    ("p06-load.jpg", "full",
     "Small in frame. Immeasurable in load. This is the labour that development economists cannot find in their datasets.",
     "Two girls carrying heavy bundles of brushwood on a mountain road"),
    ("__interlude__", "interlude",
     "While the world above negotiates chaos, the valley keeps its own time.\nThe valley has its own calendar. It does not observe the news cycle.",
     ""),
    ("p07-honey.jpg", "normal",
     "While the world outside simmers with tension, an ordinary afternoon at the honey and fruit stall stays calm and sweet.",
     "A honey and fruit stall"),
    ("p08-walk.jpg", "full",
     "On the day the city fixes its gaze upon the sky, life beneath the shadow of the mountain remains still and simple in every step forward.",
     "A mother and child walking beneath the mountain's shadow"),
    ("p09-garden.jpg", "normal",
     "Even as the world trembles, this house stands quietly, its vegetable garden growing by the season — not by the war.",
     "A house with a vegetable garden under the trees"),
    ("p10-market.jpg", "normal",
     "With war drawing close, a conversation in the market is its own proof that ordinary life persists.",
     "A conversation in the market"),
    ("p11-kebab.jpg", "normal",
     "On a day the world outside is boiling, the vendor stays busy with his stove and his customers — not because he doesn't know what is happening, but because he knows everyone still has to eat.",
     "A food vendor at his stall"),
    ("p12-cobbler.jpg", "normal",
     "War may redraw the strategy maps, but the shoe-mender's craft stays as honest as every other day.",
     "A shoe repairman in front of his shop"),
    ("p13-cook.jpg", "normal",
     "While fighter jets climb out of this town, a father still stands at the stove, cooking for his family.",
     "A cook standing at the stove"),
    ("p14-snack.jpg", "normal",
     "Gunfire is not far away, yet in a corner shop adults chat with one another and a girl picks out her snacks… this scene is utterly normal.",
     "A girl choosing snacks at a shop"),
    ("p15-board.jpg", "full",
     "Fear does not announce itself. It updates silently — column by column — under the word Delayed.",
     "An airport arrivals board showing delayed flights"),
    ("p16-gaze.jpg", "normal",
     "The scene around them looks still, yet in the children's eyes and posture something trembles, quietly.",
     "Children's gaze from a motor-cart"),
    ("p17-town.jpg", "full",
     "A small town of national strategic weight, full of ordinary people who refuse to surrender to a shifting world.",
     "The main bazaar street of Skardu"),
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
            "INSERT INTO essays(slug,title,kicker,location,date_text,"
            "summary,lede,outro,signature,status,published_at) "
            "VALUES(:slug,:title,:kicker,:location,:date_text,"
            ":summary,:lede,:outro,:signature,'published',datetime('now'))",
            ESSAY)
        eid = cur.lastrowid

        hero_rel = images.import_from_path(
            os.path.join(SRC_IMG, HERO_SRC), eid, role="hero", name="hero.jpg")
        conn.execute("UPDATE essays SET hero_image=? WHERE id=?", (hero_rel, eid))

        pos = 0
        for fname, layout, caption, alt in PLATES:
            pos += 1
            if layout == "interlude":
                conn.execute(
                    "INSERT INTO plates(essay_id,position,kind,image,layout,caption,alt)"
                    " VALUES(?,?,?,?,?,?,?)",
                    (eid, pos, "interlude", "", "normal", caption, alt))
            else:
                rel = images.import_from_path(
                    os.path.join(SRC_IMG, fname), eid, role="plate",
                    name=fname.replace("p", "plate", 1))
                conn.execute(
                    "INSERT INTO plates(essay_id,position,kind,image,layout,caption,alt)"
                    " VALUES(?,?,?,?,?,?,?)",
                    (eid, pos, "photo", rel, layout, caption, alt))
        conn.commit()
        print(f"seeded essay '{SLUG}' (id={eid}) with {len(PLATES)} plates + hero")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
