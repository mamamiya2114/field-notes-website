-- Field Notes CMS — SQLite schema
-- One file, embedded DB. Safe to re-run (IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS settings (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS essays (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  slug          TEXT UNIQUE NOT NULL,
  title         TEXT NOT NULL DEFAULT '',
  kicker        TEXT NOT NULL DEFAULT '',          -- e.g. "Photo Essay № 01 — Skardu, Pakistan"
  location      TEXT NOT NULL DEFAULT '',          -- e.g. "Skardu, Pakistan"
  date_text     TEXT NOT NULL DEFAULT '',          -- e.g. "May 2025"
  summary       TEXT NOT NULL DEFAULT '',          -- short blurb for the landing card
  lede          TEXT NOT NULL DEFAULT '',          -- intro prose, paragraphs separated by blank lines
  outro         TEXT NOT NULL DEFAULT '',          -- closing prose, paragraphs separated by blank lines
  signature     TEXT NOT NULL DEFAULT 'BUN',       -- sign-off line
  hero_image    TEXT NOT NULL DEFAULT '',          -- relative path under /uploads
  status        TEXT NOT NULL DEFAULT 'draft',     -- draft | published
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
  published_at  TEXT
);

CREATE TABLE IF NOT EXISTS plates (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  essay_id    INTEGER NOT NULL REFERENCES essays(id) ON DELETE CASCADE,
  position    INTEGER NOT NULL DEFAULT 0,
  kind        TEXT NOT NULL DEFAULT 'photo',       -- photo | interlude
  image       TEXT NOT NULL DEFAULT '',            -- relative path under /uploads (photo plates)
  layout      TEXT NOT NULL DEFAULT 'normal',      -- normal | full (photo plates)
  caption     TEXT NOT NULL DEFAULT '',
  alt         TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_plates_essay ON plates(essay_id, position);

-- Staged (unconfirmed) admin edits: every content edit is stored here first,
-- previewed on the real page, and only written to the live tables on confirm.
CREATE TABLE IF NOT EXISTS pending_edits (
  token      TEXT PRIMARY KEY,
  kind       TEXT NOT NULL,                        -- essay_meta | plate_update | plate_add | essay_hero | site
  payload    TEXT NOT NULL,                        -- JSON
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Privacy-friendly analytics. We never store IP addresses.
-- visitor_hash = sha256(day + daily_salt + ip + ua); the salt rotates daily and
-- is the only way to correlate, so the data cannot be traced back to a person.
CREATE TABLE IF NOT EXISTS visits (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  day          TEXT NOT NULL,                      -- YYYY-MM-DD (server local)
  ts           TEXT NOT NULL DEFAULT (datetime('now')),
  path         TEXT NOT NULL,
  essay_slug   TEXT,                               -- set when path is an essay
  referrer     TEXT NOT NULL DEFAULT '',           -- referrer host only (no query)
  country      TEXT NOT NULL DEFAULT 'XX',         -- 2-letter, from proxy header; XX = unknown
  device       TEXT NOT NULL DEFAULT 'desktop',    -- desktop | mobile | tablet | bot
  browser      TEXT NOT NULL DEFAULT 'Other',
  visitor_hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_visits_day  ON visits(day);
CREATE INDEX IF NOT EXISTS idx_visits_slug ON visits(essay_slug);

CREATE TABLE IF NOT EXISTS daily_salts (
  day  TEXT PRIMARY KEY,
  salt TEXT NOT NULL
);

-- Editable landing-page content (hero, about, footer). Key/value so the owner
-- can edit copy + images from /admin/site without touching templates.
-- A missing/blank key falls back to the built-in default (see SITE_DEFAULTS).
CREATE TABLE IF NOT EXISTS site_content (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL DEFAULT ''
);

-- "From the archive" gallery on the landing page, managed at /admin/gallery.
-- `image` is a ready-to-serve URL: /uploads/gallery/… for uploads, or a bundled
-- /static/images/gNN.jpg default. Ordered by `position`.
CREATE TABLE IF NOT EXISTS gallery (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  position   INTEGER NOT NULL DEFAULT 0,
  image      TEXT NOT NULL,
  alt        TEXT NOT NULL DEFAULT '',   -- short accessibility text
  note       TEXT NOT NULL DEFAULT '',   -- the owner's written note, shown in the lightbox
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_gallery_pos ON gallery(position);
