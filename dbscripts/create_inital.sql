CREATE TABLE IF NOT EXISTS scores (
  id integer PRIMARY KEY AUTOINCREMENT,
  twitch_username text,
  channel text,
  ts integer,
  score integer
);

CREATE TABLE IF NOT EXISTS whitelist (
  id integer PRIMARY KEY AUTOINCREMENT,
  whitelisted_twitch_user text,
  whitelisted_by text
)
