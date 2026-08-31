-- Local Experience & Attraction Recommender schema (student-3)
-- Owned exclusively by the student-3 database microservice.
-- Other services must go through /api/data/* on this service, never open this file directly.

CREATE TABLE IF NOT EXISTS attractions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,       -- e.g. sight, restaurant, activity
    description TEXT,
    rating REAL
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attraction_id INTEGER NOT NULL,
    rating REAL,
    comment TEXT,
    FOREIGN KEY (attraction_id) REFERENCES attractions(id)
);
