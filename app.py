"""Field Notes CMS — Flask app.

Public site (landing + essays) and a password-protected admin where the owner
uploads photos, writes Thai/English captions, and publishes essays. Every public
page view is logged through the privacy-friendly analytics in analytics.py and
shown on the admin dashboard.

Run locally:   python3 app.py
Production:    gunicorn app:app
"""
import os
import re
import time
import hmac
import secrets
import functools
import datetime
from urllib.parse import urlparse

from flask import (Flask, g, request, session, redirect, url_for, abort,
                   render_template, send_from_directory, flash, jsonify)
from werkzeug.security import check_password_hash, generate_password_hash

import db
import images
import analytics

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Set FN_HTTPS=1 in production (behind HTTPS) so cookies are Secure-only and HSTS
# is sent. Leave unset for local http://localhost development.
HTTPS = os.environ.get("FN_HTTPS", "").lower() in ("1", "true", "yes")

app = Flask(__name__)
db.init_db()
app.secret_key = db.get_or_create_secret_key()
app.config.update(
    MAX_CONTENT_LENGTH=40 * 1024 * 1024,        # 40 MB per upload (DoS guard)
    UPLOAD_DIR=images.UPLOAD_DIR,
    SESSION_COOKIE_HTTPONLY=True,               # JS can't read the session cookie (XSS theft)
    SESSION_COOKIE_SAMESITE="Lax",              # cross-site POSTs don't carry the cookie (CSRF)
    SESSION_COOKIE_SECURE=HTTPS,                 # cookie only over HTTPS in production
    PERMANENT_SESSION_LIFETIME=datetime.timedelta(days=14),
    MAX_FORM_MEMORY_SIZE=2 * 1024 * 1024,
)
app.teardown_appcontext(db.close_db)


# --------------------------------------------------------------------------
# CSRF protection (dependency-free, double-submit token in the session)
# --------------------------------------------------------------------------

def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(32)
    return session["csrf"]


@app.before_request
def csrf_protect():
    """Reject state-changing requests without a valid token.

    Combined with SameSite=Lax cookies this gives layered CSRF defense. /subscribe
    is public (no privileged action) and is exempted; everything else that mutates
    state must present the session token.
    """
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return
    if request.path == "/subscribe":
        return
    sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token", "")
    # compare as bytes: compare_digest raises TypeError on non-ASCII str input
    if not session.get("csrf") or not hmac.compare_digest(
            sent.encode("utf-8", "replace"), session["csrf"].encode("utf-8")):
        abort(400, description="CSRF token missing or invalid")


app.jinja_env.globals["csrf_token"] = csrf_token


def nl2br(value):
    """Escape user text, then turn newlines into <br>. Prevents stored XSS while
    preserving intentional line breaks (replaces the unsafe `| replace | safe`)."""
    import markupsafe
    parts = (value or "").split("\n")
    return markupsafe.Markup("<br>".join(markupsafe.escape(p) for p in parts))


def emphasize(value):
    """Escape, then render *word* as <em>word</em>. Lets the owner emphasize a word
    (e.g. the hero headline) from plain text without any HTML-injection risk."""
    import markupsafe
    out, i, n = [], 0, len(value or "")
    text = value or ""
    while i < n:
        star = text.find("*", i)
        if star == -1:
            out.append(markupsafe.escape(text[i:]))
            break
        end = text.find("*", star + 1)
        if end == -1:
            out.append(markupsafe.escape(text[i:]))
            break
        out.append(markupsafe.escape(text[i:star]))
        out.append(markupsafe.Markup("<em>") + markupsafe.escape(text[star + 1:end]) + markupsafe.Markup("</em>"))
        i = end + 1
    return markupsafe.Markup("").join(out)


app.jinja_env.filters["nl2br"] = nl2br
app.jinja_env.filters["emphasize"] = emphasize


# --------------------------------------------------------------------------
# Editable landing-page content (site_content table + built-in defaults)
# --------------------------------------------------------------------------

SITE_DEFAULTS = {
    "hero_kicker": "A Photo Essay Journal",
    "hero_title": "Stories told in *light*, written in place.",
    "hero_lede": "Field Notes is a personal archive of photo essays — slow observations "
                 "of mountain valleys, bazaar towns, and the people who move through them. "
                 "Part research notebook, part visual diary.",
    "hero_caption": "First Light on the Valley, Skardu 2025",
    "hero_image": "/static/images/hero-valley.jpg",
    "about_kicker": "About",
    "about_heading": "Notes from behind the lens",
    "about_body": "I'm a researcher and photographer documenting how places change — and "
                  "what photographs can hold that words cannot. Field Notes began as a "
                  "private notebook during fieldwork and slowly became this public archive.\n\n"
                  "Each essay pairs a photographic series with written field notes: "
                  "observations, fragments of conversation, and references for those who "
                  "want to go deeper.",
    "about_signature": "— BUN",
    "about_image": "/static/images/about.jpg",
    "subscribe_heading": "Get new essays by email",
    "subscribe_tagline": "One letter a month. Photographs first, words second. No noise.",
    "footer_tagline": "A photo essay journal by BUN",
    "footer_instagram": "",
    "footer_contact": "",
}

# keys that hold an image path (handled as uploads, not plain text)
SITE_IMAGE_KEYS = ("hero_image", "about_image")


def get_site():
    """Return all editable site content, defaults filled in. A blank stored value
    falls back to its default so a section is never accidentally empty."""
    data = dict(SITE_DEFAULTS)
    try:
        for r in db.get_db().execute("SELECT key, value FROM site_content").fetchall():
            if r["key"] in data and (r["value"] or "").strip():
                data[r["key"]] = r["value"]
    except Exception:
        pass
    return data


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

ROMAN = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"),
         (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"),
         (5, "V"), (4, "IV"), (1, "I")]


def to_roman(n):
    out, i = "", n
    for val, sym in ROMAN:
        while i >= val:
            out += sym
            i -= val
    return out


def slugify(text):
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9฀-๿]+", "-", text)   # keep Thai letters
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "essay"


def unique_slug(base, essay_id=None):
    base = slugify(base)
    cur = base
    n = 2
    while True:
        row = db.get_db().execute(
            "SELECT id FROM essays WHERE slug=? AND id IS NOT ?", (cur, essay_id)
        ).fetchone()
        if not row:
            return cur
        cur = f"{base}-{n}"
        n += 1


def paragraphs(text):
    return [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]


def get_essay(essay_id):
    return db.get_db().execute("SELECT * FROM essays WHERE id=?", (essay_id,)).fetchone()


def get_plates(essay_id):
    return db.get_db().execute(
        "SELECT * FROM plates WHERE essay_id=? ORDER BY position, id", (essay_id,)
    ).fetchall()


def build_plates_view(plates):
    """Attach an auto roman-numeral label to photo plates (interludes skipped)."""
    out, n = [], 0
    for p in plates:
        d = dict(p)
        if p["kind"] == "photo":
            n += 1
            d["num"] = "PLATE " + to_roman(n)
        out.append(d)
    return out


app.jinja_env.globals.update(paragraphs=paragraphs)


@app.context_processor
def inject_globals():
    return {"now_year": datetime.date.today().year, "site": get_site()}


# --------------------------------------------------------------------------
# auth
# --------------------------------------------------------------------------

def login_required(view):
    @functools.wraps(view)
    def wrapped(*a, **kw):
        if not session.get("admin"):
            return redirect(url_for("login", next=request.path))
        return view(*a, **kw)
    return wrapped


def _is_safe_next(target):
    """Allow only same-site relative redirects — blocks open-redirect via ?next=."""
    if not target:
        return False
    parsed = urlparse(target)
    return not parsed.scheme and not parsed.netloc and target.startswith("/") \
        and not target.startswith("//")


# very small brute-force throttle (per worker, in-memory): lock after 7 fails / 15 min
_login_fails = {}
_LOCK_AFTER, _LOCK_WINDOW = 7, 900


def _login_blocked(ip):
    fails = [t for t in _login_fails.get(ip, []) if time.time() - t < _LOCK_WINDOW]
    _login_fails[ip] = fails
    return len(fails) >= _LOCK_AFTER


def _record_login_fail(ip):
    _login_fails.setdefault(ip, []).append(time.time())


@app.route("/admin/login", methods=["GET", "POST"])
def login():
    pw_hash = db.get_setting("admin_password")
    needs_setup = pw_hash is None
    ip = analytics._client_ip(request)
    if request.method == "POST":
        if _login_blocked(ip):
            flash("พยายามเข้าระบบบ่อยเกินไป — รอสักครู่แล้วลองใหม่")
            return render_template("admin/login.html", needs_setup=needs_setup), 429
        password = request.form.get("password", "")
        if needs_setup:
            if len(password) < 8:
                flash("ตั้งรหัสผ่านอย่างน้อย 8 ตัวอักษร")
            else:
                db.set_setting("admin_password",
                               generate_password_hash(password, method="pbkdf2:sha256"))
                session.clear()
                session["admin"] = True
                session.permanent = True
                return redirect(url_for("dashboard"))
        elif check_password_hash(pw_hash, password):
            session.clear()                 # rotate session id on login (fixation guard)
            session["admin"] = True
            session.permanent = True
            nxt = request.args.get("next")
            return redirect(nxt if _is_safe_next(nxt) else url_for("dashboard"))
        else:
            _record_login_fail(ip)
            flash("รหัสผ่านไม่ถูกต้อง")
    return render_template("admin/login.html", needs_setup=needs_setup)


@app.route("/admin/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


# --------------------------------------------------------------------------
# admin — essays
# --------------------------------------------------------------------------

@app.route("/admin")
@login_required
def dashboard():
    rows = db.get_db().execute(
        "SELECT e.*, (SELECT COUNT(*) FROM plates p WHERE p.essay_id=e.id "
        "             AND p.kind='photo') AS photo_count, "
        "(SELECT COUNT(*) FROM visits v WHERE v.essay_slug=e.slug) AS views "
        "FROM essays e ORDER BY (status='published') DESC, updated_at DESC"
    ).fetchall()
    return render_template("admin/dashboard.html", essays=rows)


@app.route("/admin/essays/new", methods=["POST"])
@login_required
def essay_new():
    title_th = request.form.get("title_th", "").strip() or "เรื่องใหม่"
    slug = unique_slug(request.form.get("title_en") or title_th)
    cur = db.get_db()
    cur.execute(
        "INSERT INTO essays(slug, title_th, kicker) VALUES(?,?,?)",
        (slug, title_th, "Photo Essay"),
    )
    cur.commit()
    eid = cur.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    return redirect(url_for("essay_edit", essay_id=eid))


@app.route("/admin/essays/<int:essay_id>")
@login_required
def essay_edit(essay_id):
    essay = get_essay(essay_id)
    if not essay:
        abort(404)
    plates = build_plates_view(get_plates(essay_id))
    return render_template("admin/editor.html", essay=essay, plates=plates)


@app.route("/admin/essays/<int:essay_id>/save", methods=["POST"])
@login_required
def essay_save(essay_id):
    essay = get_essay(essay_id)
    if not essay:
        abort(404)
    f = request.form
    new_slug = essay["slug"]
    if f.get("slug", "").strip():
        new_slug = unique_slug(f["slug"], essay_id)
    db.get_db().execute(
        "UPDATE essays SET title_th=?, title_en=?, kicker=?, location=?, date_text=?, "
        "summary_en=?, lede=?, outro=?, signature=?, slug=?, updated_at=datetime('now') "
        "WHERE id=?",
        (f.get("title_th", "").strip(), f.get("title_en", "").strip(),
         f.get("kicker", "").strip(), f.get("location", "").strip(),
         f.get("date_text", "").strip(), f.get("summary_en", "").strip(),
         f.get("lede", "").strip(), f.get("outro", "").strip(),
         f.get("signature", "").strip() or "BUN", new_slug, essay_id),
    )
    db.get_db().commit()
    flash("บันทึกแล้ว")
    return redirect(url_for("essay_edit", essay_id=essay_id))


@app.route("/admin/essays/<int:essay_id>/hero", methods=["POST"])
@login_required
def essay_hero(essay_id):
    essay = get_essay(essay_id)
    if not essay:
        abort(404)
    file = request.files.get("hero")
    if file and file.filename:
        try:
            rel = images.process_upload(file, essay_id, role="hero")
        except ValueError as e:
            flash(str(e))
            return redirect(url_for("essay_edit", essay_id=essay_id))
        if essay["hero_image"]:
            images.delete_upload(essay["hero_image"])
        db.get_db().execute(
            "UPDATE essays SET hero_image=?, updated_at=datetime('now') WHERE id=?",
            (rel, essay_id))
        db.get_db().commit()
        flash("อัปเดตรูปปกแล้ว")
    return redirect(url_for("essay_edit", essay_id=essay_id))


@app.route("/admin/essays/<int:essay_id>/publish", methods=["POST"])
@login_required
def essay_publish(essay_id):
    essay = get_essay(essay_id)
    if not essay:
        abort(404)
    publish = request.form.get("action") == "publish"
    if publish:
        db.get_db().execute(
            "UPDATE essays SET status='published', published_at=COALESCE(published_at, "
            "datetime('now')), updated_at=datetime('now') WHERE id=?", (essay_id,))
        flash("เผยแพร่แล้ว — ดูได้ที่หน้าเว็บจริง")
    else:
        db.get_db().execute(
            "UPDATE essays SET status='draft', updated_at=datetime('now') WHERE id=?",
            (essay_id,))
        flash("เปลี่ยนเป็นฉบับร่างแล้ว")
    db.get_db().commit()
    return redirect(url_for("essay_edit", essay_id=essay_id))


@app.route("/admin/essays/<int:essay_id>/delete", methods=["POST"])
@login_required
def essay_delete(essay_id):
    essay = get_essay(essay_id)
    if not essay:
        abort(404)
    for p in get_plates(essay_id):
        images.delete_upload(p["image"])
    images.delete_upload(essay["hero_image"])
    images.delete_essay_dir(essay_id)
    db.get_db().execute("DELETE FROM essays WHERE id=?", (essay_id,))
    db.get_db().commit()
    flash("ลบเรื่องแล้ว")
    return redirect(url_for("dashboard"))


# --------------------------------------------------------------------------
# admin — plates
# --------------------------------------------------------------------------

@app.route("/admin/essays/<int:essay_id>/plates", methods=["POST"])
@login_required
def plate_add(essay_id):
    essay = get_essay(essay_id)
    if not essay:
        abort(404)
    kind = request.form.get("kind", "photo")
    nextpos = (db.get_db().execute(
        "SELECT COALESCE(MAX(position), 0) + 1 AS n FROM plates WHERE essay_id=?",
        (essay_id,)).fetchone()["n"])
    image_rel = ""
    if kind == "photo":
        file = request.files.get("image")
        if not (file and file.filename):
            flash("เลือกไฟล์รูปก่อนเพิ่มแผ่นภาพ")
            return redirect(url_for("essay_edit", essay_id=essay_id))
        try:
            image_rel = images.process_upload(file, essay_id, role="plate")
        except ValueError as e:
            flash(str(e))
            return redirect(url_for("essay_edit", essay_id=essay_id))
    db.get_db().execute(
        "INSERT INTO plates(essay_id, position, kind, image, layout, caption_th, "
        "caption_en, alt) VALUES(?,?,?,?,?,?,?,?)",
        (essay_id, nextpos, kind, image_rel,
         request.form.get("layout", "normal"),
         request.form.get("caption_th", "").strip(),
         request.form.get("caption_en", "").strip(),
         request.form.get("alt", "").strip()),
    )
    db.get_db().execute("UPDATE essays SET updated_at=datetime('now') WHERE id=?", (essay_id,))
    db.get_db().commit()
    return redirect(url_for("essay_edit", essay_id=essay_id) + "#plates")


@app.route("/admin/plates/<int:plate_id>/update", methods=["POST"])
@login_required
def plate_update(plate_id):
    plate = db.get_db().execute("SELECT * FROM plates WHERE id=?", (plate_id,)).fetchone()
    if not plate:
        abort(404)
    db.get_db().execute(
        "UPDATE plates SET caption_th=?, caption_en=?, layout=?, alt=? WHERE id=?",
        (request.form.get("caption_th", "").strip(),
         request.form.get("caption_en", "").strip(),
         request.form.get("layout", "normal"),
         request.form.get("alt", "").strip(), plate_id),
    )
    db.get_db().commit()
    return redirect(url_for("essay_edit", essay_id=plate["essay_id"]) + "#plates")


@app.route("/admin/plates/<int:plate_id>/replace", methods=["POST"])
@login_required
def plate_replace(plate_id):
    plate = db.get_db().execute("SELECT * FROM plates WHERE id=?", (plate_id,)).fetchone()
    if not plate:
        abort(404)
    file = request.files.get("image")
    if file and file.filename:
        try:
            rel = images.process_upload(file, plate["essay_id"], role="plate")
        except ValueError as e:
            flash(str(e))
            return redirect(url_for("essay_edit", essay_id=plate["essay_id"]) + "#plates")
        images.delete_upload(plate["image"])
        db.get_db().execute("UPDATE plates SET image=? WHERE id=?", (rel, plate_id))
        db.get_db().commit()
    return redirect(url_for("essay_edit", essay_id=plate["essay_id"]) + "#plates")


@app.route("/admin/plates/<int:plate_id>/delete", methods=["POST"])
@login_required
def plate_delete(plate_id):
    plate = db.get_db().execute("SELECT * FROM plates WHERE id=?", (plate_id,)).fetchone()
    if not plate:
        abort(404)
    images.delete_upload(plate["image"])
    db.get_db().execute("DELETE FROM plates WHERE id=?", (plate_id,))
    db.get_db().commit()
    return redirect(url_for("essay_edit", essay_id=plate["essay_id"]) + "#plates")


@app.route("/admin/plates/<int:plate_id>/move", methods=["POST"])
@login_required
def plate_move(plate_id):
    cur = db.get_db()
    plate = cur.execute("SELECT * FROM plates WHERE id=?", (plate_id,)).fetchone()
    if not plate:
        abort(404)
    direction = request.form.get("dir")
    op = "<" if direction == "up" else ">"
    order = "DESC" if direction == "up" else "ASC"
    neighbour = cur.execute(
        f"SELECT * FROM plates WHERE essay_id=? AND position {op} ? "
        f"ORDER BY position {order} LIMIT 1",
        (plate["essay_id"], plate["position"]),
    ).fetchone()
    if neighbour:
        cur.execute("UPDATE plates SET position=? WHERE id=?",
                    (neighbour["position"], plate["id"]))
        cur.execute("UPDATE plates SET position=? WHERE id=?",
                    (plate["position"], neighbour["id"]))
        cur.commit()
    return redirect(url_for("essay_edit", essay_id=plate["essay_id"]) + "#plates")


# --------------------------------------------------------------------------
# admin — analytics
# --------------------------------------------------------------------------

@app.route("/admin/stats")
@login_required
def stats():
    days = request.args.get("days", 30, type=int)
    days = max(1, min(days, 365))
    data = analytics.summary(days)
    return render_template("admin/stats.html", s=data,
                           max_views=max([d["views"] for d in data["series"]] + [1]))


# --------------------------------------------------------------------------
# admin — editable landing content
# --------------------------------------------------------------------------

@app.route("/admin/site")
@login_required
def site_edit():
    return render_template("admin/site.html", defaults=SITE_DEFAULTS)


@app.route("/admin/site/save", methods=["POST"])
@login_required
def site_save():
    cur = db.get_db()
    for key in SITE_DEFAULTS:
        if key in SITE_IMAGE_KEYS:
            continue
        cur.execute(
            "INSERT INTO site_content(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, request.form.get(key, "").strip()))
    for key in SITE_IMAGE_KEYS:
        file = request.files.get(key)
        if file and file.filename:
            try:
                rel = images.process_site_upload(
                    file, role=("hero" if key == "hero_image" else "card"))
            except ValueError as e:
                flash(str(e))
                continue
            # remove the previously uploaded file for this slot (not static defaults)
            old = cur.execute("SELECT value FROM site_content WHERE key=?", (key,)).fetchone()
            if old and (old["value"] or "").startswith("/uploads/site/"):
                images.delete_upload(old["value"][len("/uploads/"):])
            cur.execute(
                "INSERT INTO site_content(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, "/uploads/" + rel))
    cur.commit()
    flash("บันทึกหน้าเว็บแล้ว — ดูผลได้ที่หน้าเว็บจริง")
    return redirect(url_for("site_edit"))


# --------------------------------------------------------------------------
# public site
# --------------------------------------------------------------------------

@app.route("/")
def landing():
    rows = db.get_db().execute(
        "SELECT * FROM essays WHERE status='published' "
        "ORDER BY published_at DESC, id DESC").fetchall()
    featured = rows[0] if rows else None
    recent = rows[1:] if len(rows) > 1 else []
    gallery = sorted(
        f for f in os.listdir(os.path.join(BASE_DIR, "static", "images"))
        if re.match(r"g\d+\.jpg$", f)
    ) if os.path.isdir(os.path.join(BASE_DIR, "static", "images")) else []
    return render_template("landing.html", featured=featured, recent=recent,
                           gallery=gallery)


@app.route("/essay/<slug>")
def essay_view(slug):
    essay = db.get_db().execute(
        "SELECT * FROM essays WHERE slug=?", (slug,)).fetchone()
    if not essay:
        abort(404)
    if essay["status"] != "published" and not session.get("admin"):
        abort(404)
    plates = build_plates_view(get_plates(essay["id"]))
    return render_template("essay.html", essay=essay, plates=plates,
                           preview=(essay["status"] != "published"))


@app.route("/subscribe", methods=["POST"])
def subscribe():
    email = (request.form.get("email") or "").strip().lower()
    ok = bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))
    if ok:
        try:
            db.get_db().execute("INSERT OR IGNORE INTO subscribers(email) VALUES(?)", (email,))
            db.get_db().commit()
        except Exception:
            ok = False
    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify(ok=ok)
    flash("ขอบคุณ — คุณอยู่ในรายชื่อแล้ว ✦" if ok else "อีเมลไม่ถูกต้อง")
    return redirect(url_for("landing") + "#subscribe")


@app.route("/uploads/<path:rel>")
def uploads(rel):
    return send_from_directory(app.config["UPLOAD_DIR"], rel)


@app.route("/healthz")
def healthz():
    return "ok", 200


@app.route("/robots.txt")
def robots():
    body = (f"User-agent: *\nDisallow: /admin\n"
            f"Sitemap: {request.url_root}sitemap.xml\n")
    return body, 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.route("/sitemap.xml")
def sitemap():
    rows = db.get_db().execute(
        "SELECT slug, COALESCE(updated_at, published_at) AS mod FROM essays "
        "WHERE status='published' ORDER BY published_at DESC").fetchall()
    urls = [f"<url><loc>{request.url_root}</loc></url>"]
    for r in rows:
        lastmod = (r["mod"] or "")[:10]
        urls.append(
            f"<url><loc>{request.url_root}essay/{r['slug']}</loc>"
            + (f"<lastmod>{lastmod}</lastmod>" if lastmod else "") + "</url>")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
           + "".join(urls) + "</urlset>")
    return xml, 200, {"Content-Type": "application/xml; charset=utf-8"}


# --------------------------------------------------------------------------
# analytics hook — log public HTML page views only
# --------------------------------------------------------------------------

@app.after_request
def log_visit(response):
    try:
        if request.method != "GET":
            return response
        if response.status_code != 200:
            return response
        ctype = response.headers.get("Content-Type", "")
        if "text/html" not in ctype:
            return response
        path = request.path
        if path.startswith(("/admin", "/uploads", "/static", "/healthz")):
            return response
        if session.get("admin"):
            return response      # don't count the owner's own browsing/previews
        slug = None
        if path.startswith("/essay/"):
            slug = path[len("/essay/"):].strip("/")
        analytics.record_visit(request, path, slug)
    except Exception:
        # never let analytics break a page
        pass
    return response


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    # CSP: allow our own inline CSS/JS (the site is single-file by design) + Google
    # Fonts; block external scripts, framing, plugins, and form posts off-site.
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' data:; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; "
        "script-src 'self' 'unsafe-inline'; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'"
    )
    if HTTPS:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.errorhandler(400)
def bad_request(e):
    return render_template("404.html"), 400


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(413)
def too_large(e):
    flash("ไฟล์ใหญ่เกินไป (สูงสุด 40MB ต่อไฟล์)")
    return render_template("404.html"), 413


@app.errorhandler(500)
def server_error(e):
    return render_template("404.html"), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=bool(os.environ.get("FN_DEBUG")))
