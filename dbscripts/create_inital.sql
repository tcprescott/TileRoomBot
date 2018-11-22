CREATE TABLE IF NOT EXISTS scores (
  id integer PRIMARY KEY AUTOINCREMENT,
  twitch_username text,
  channel text,
  ts integer,
  score integer
);
