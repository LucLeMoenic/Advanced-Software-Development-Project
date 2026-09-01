-- Student 5 - Travel Logistics & Advisory Service
-- Schema for the SQLite database microservice.
--
-- NOTE: foreign key enforcement is a per-connection setting in SQLite, so the
-- application also issues "PRAGMA foreign_keys = ON" on every connection it
-- opens. The pragma below only covers the connection that runs this script.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS destinations (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    country           TEXT    NOT NULL,
    visa_requirement  TEXT    NOT NULL,
    notes             TEXT
);

CREATE TABLE IF NOT EXISTS weather_notes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    destination_id  INTEGER NOT NULL REFERENCES destinations(id) ON DELETE CASCADE,
    season          TEXT    NOT NULL,
    notes           TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS transit_options (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    destination_id  INTEGER NOT NULL REFERENCES destinations(id) ON DELETE CASCADE,
    type            TEXT    NOT NULL,
    details         TEXT    NOT NULL
);
