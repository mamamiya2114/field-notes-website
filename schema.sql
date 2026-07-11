-- Field Notes CMS — SQLite schema
-- One file, embedded DB. Safe to re-run (IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS settings (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS essays (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  slug          TEXT UNIQUE NOT NULL,
  title_th      TEXT NOT NULL DEFAULT '',
  title_en      TEXT NOT NULL DEFAULT '',
  kicker        TEXT NOT NULL DEFAULT '',          -- e.g. "Photo Essay № 01 — Skardu, Pakistan"
  location      TEXT NOT NULL DEFAULT '',          -- e.g. "Skardu, Pakistan"
  date_text     TEXT NOT NULL DEFAULT '',          -- e.g. "พฤษภาคม 2568"
  summary_en    TEXT NOT NULL DEFAULT '',          -- short English blurb for the landing card
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
  caption_th  TEXT NOT NULL DEFAULT '',
  caption_en  TEXT NOT NULL DEFAULT '',
  alt         TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_plates_essay ON plates(essay_id, position);

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

CREATE TABLE IF NOT EXISTS subscribers (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  email      TEXT UNIQUE NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Editable landing-page content (hero, about, subscribe, footer). Key/value so
-- the owner can edit copy + images from /admin/site without touching templates.
-- A missing/blank key falls back to the built-in default (see SITE_DEFAULTS).
CREATE TABLE IF NOT EXISTS site_content (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL DEFAULT ''
);
