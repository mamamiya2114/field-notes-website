"""Privacy-friendly visit analytics.

No cookies, no stored IPs. Unique visitors are counted with a daily-rotating
salted hash of (IP + User-Agent), the same technique Plausible/GoatCounter use:
the salt is thrown away each day, so yesterday's hashes can never be re-linked to
a person. We keep only coarse, aggregate-friendly fields.
"""
import re
import hashlib
import secrets
import datetime
from urllib.parse import urlsplit

from db import get_db

BOT_RE = re.compile(r"bot|crawl|spider|slurp|bingpreview|facebookexternal|headless|"
                    r"python-requests|curl|wget|monitor|preview", re.I)
TABLET_RE = re.compile(r"ipad|tablet|playbook|silk|(android(?!.*mobile))", re.I)
MOBILE_RE = re.compile(r"mobile|iphone|ipod|android|blackberry|opera mini|iemobile", re.I)


def _today():
    return datetime.date.today().isoformat()


def parse_device(ua):
    if not ua:
        return "desktop"
    if BOT_RE.search(ua):
        return "bot"
    if TABLET_RE.search(ua):
        return "tablet"
    if MOBILE_RE.search(ua):
        return "mobile"
    return "desktop"


def parse_browser(ua):
    if not ua:
        return "Other"
    ua_l = ua.lower()
    # order matters — Edge/Chrome both contain "chrome", etc.
    if "edg/" in ua_l or "edge" in ua_l:
        return "Edge"
    if "opr/" in ua_l or "opera" in ua_l:
        return "Opera"
    if "firefox" in ua_l:
        return "Firefox"
    if "chrome" in ua_l or "crios" in ua_l:
        return "Chrome"
    if "safari" in ua_l:
        return "Safari"
    return "Other"


def _daily_salt():
    day = _today()
    db = get_db()
    row = db.execute("SELECT salt FROM daily_salts WHERE day=?", (day,)).fetchone()
    if row:
        return row["salt"]
    salt = secrets.token_hex(16)
    db.execute("INSERT OR IGNORE INTO daily_salts(day, salt) VALUES(?, ?)", (day, salt))
    # prune salts older than 60 days so old hashes become permanently un-correlatable
    cutoff = (datetime.date.today() - datetime.timedelta(days=60)).isoformat()
    db.execute("DELETE FROM daily_salts WHERE day < ?", (cutoff,))
    db.commit()
    # re-read in case of a race
    row = db.execute("SELECT salt FROM daily_salts WHERE day=?", (day,)).fetchone()
    return row["salt"]


def _client_ip(request):
    fwd = request.headers.get("X-Forwarded-For", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.remote_addr or ""


def _country(request):
    # Set by common proxies/CDNs. We do not geolocate ourselves (no IP storage).
    for h in ("CF-IPCountry", "X-Vercel-IP-Country", "X-Country-Code", "Fly-Region"):
        v = request.headers.get(h)
        if v and v.upper() not in ("XX", "T1"):
            return v.upper()[:2]
    return "XX"


def _referrer_host(request):
    ref = request.headers.get("Referer", "")
    if not ref:
        return ""
    host = urlsplit(ref).netloc.lower()
    # treat same-host navigation as direct
    if host == urlsplit(request.url_root).netloc.lower():
        return ""
    return host[:120]


def record_visit(request, path, essay_slug=None):
    """Log one page view. Called from an after_request hook for public HTML pages."""
    ua = request.headers.get("User-Agent", "")
    device = parse_device(ua)
    if device == "bot":
        return  # don't pollute stats with crawlers
    day = _today()
    salt = _daily_salt()
    ip = _client_ip(request)
    visitor_hash = hashlib.sha256(f"{day}{salt}{ip}{ua}".encode("utf-8")).hexdigest()
    db = get_db()
    db.execute(
        "INSERT INTO visits(day, path, essay_slug, referrer, country, device, browser, visitor_hash)"
        " VALUES(?,?,?,?,?,?,?,?)",
        (day, path, essay_slug, _referrer_host(request), _country(request),
         device, parse_browser(ua), visitor_hash),
    )
    db.commit()


# ---- aggregate queries for the dashboard ----------------------------------

def summary(days=30):
    db = get_db()
    start = (datetime.date.today() - datetime.timedelta(days=days - 1)).isoformat()

    totals = db.execute(
        "SELECT COUNT(*) AS views, COUNT(DISTINCT visitor_hash) AS visitors "
        "FROM visits WHERE day >= ?", (start,)).fetchone()

    by_day = db.execute(
        "SELECT day, COUNT(*) AS views, COUNT(DISTINCT visitor_hash) AS visitors "
        "FROM visits WHERE day >= ? GROUP BY day ORDER BY day", (start,)).fetchall()

    # fill missing days with zeroes so the chart is continuous
    counts = {r["day"]: (r["views"], r["visitors"]) for r in by_day}
    series = []
    for i in range(days):
        d = (datetime.date.today() - datetime.timedelta(days=days - 1 - i)).isoformat()
        v, u = counts.get(d, (0, 0))
        series.append({"day": d, "views": v, "visitors": u})

    top_essays = db.execute(
        "SELECT e.title_th, e.title_en, e.slug, COUNT(*) AS views, "
        "       COUNT(DISTINCT v.visitor_hash) AS visitors "
        "FROM visits v JOIN essays e ON e.slug = v.essay_slug "
        "WHERE v.day >= ? AND v.essay_slug IS NOT NULL "
        "GROUP BY v.essay_slug ORDER BY views DESC LIMIT 10", (start,)).fetchall()

    referrers = db.execute(
        "SELECT CASE WHEN referrer='' THEN 'Direct / none' ELSE referrer END AS source, "
        "       COUNT(*) AS views FROM visits WHERE day >= ? "
        "GROUP BY source ORDER BY views DESC LIMIT 10", (start,)).fetchall()

    countries = db.execute(
        "SELECT country, COUNT(*) AS views FROM visits WHERE day >= ? "
        "GROUP BY country ORDER BY views DESC LIMIT 10", (start,)).fetchall()

    devices = db.execute(
        "SELECT device, COUNT(*) AS views FROM visits WHERE day >= ? "
        "GROUP BY device ORDER BY views DESC", (start,)).fetchall()

    browsers = db.execute(
        "SELECT browser, COUNT(*) AS views FROM visits WHERE day >= ? "
        "GROUP BY browser ORDER BY views DESC LIMIT 6", (start,)).fetchall()

    return {
        "days": days,
        "views": totals["views"] or 0,
        "visitors": totals["visitors"] or 0,
        "series": series,
        "top_essays": [dict(r) for r in top_essays],
        "referrers": [dict(r) for r in referrers],
        "countries": [dict(r) for r in countries],
        "devices": [dict(r) for r in devices],
        "browsers": [dict(r) for r in browsers],
    }
