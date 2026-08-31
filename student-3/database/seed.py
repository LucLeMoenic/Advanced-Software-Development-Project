"""Inserts sample attractions and reviews for local demo/grading use.

Run directly: `python seed.py`
Safe to re-run: it only seeds when the attractions table is empty, so it
won't duplicate rows on every container restart.
"""

from db import ensure_schema, get_connection

ATTRACTIONS = [
    ("Sydney Opera House", "sight", "Iconic sail-shaped performing arts venue on Sydney Harbour.", 4.7),
    ("Bondi to Coogee Coastal Walk", "activity", "6km clifftop walking track past Sydney's most famous beaches.", 4.8),
    ("Chat Thai Sydney CBD", "restaurant", "Busy, no-frills Thai restaurant popular with locals and students.", 4.3),
    ("Taronga Zoo Sydney", "activity", "Harbourside zoo with ferry access and views back to the city skyline.", 4.5),
    ("The Rocks Markets", "sight", "Historic cobblestone precinct with weekend craft and food stalls.", 4.2),
    ("Mr. Wong", "restaurant", "Upscale Cantonese dining in a converted Sydney CBD warehouse.", 4.6),
    ("Federation Square", "sight", "Melbourne's civic square hosting events, galleries, and public screens.", 4.1),
    ("Melbourne Street Art Laneway Tour", "activity", "Guided walk through Hosier Lane and nearby graffiti-covered laneways.", 4.6),
    ("Chin Chin Melbourne", "restaurant", "Loud, popular modern Thai/Asian restaurant on Flinders Lane.", 4.4),
    ("Royal Botanic Gardens Victoria", "sight", "Sprawling gardens on the Yarra River, free to enter.", 4.7),
    ("Queen Victoria Market", "restaurant", "Historic open-air market with food stalls, produce, and deli halls.", 4.3),
    ("Great Ocean Road Day Trip", "activity", "Full-day coastal drive from Melbourne past the Twelve Apostles.", 4.8),
]

REVIEWS = [
    (1, 5.0, "Breathtaking at sunset, worth the hype."),
    (1, 4.0, "Very crowded but the architecture is stunning."),
    (2, 5.0, "Best free thing to do in Sydney, go early to avoid heat."),
    (3, 4.0, "Cheap, fast, and genuinely good pad see ew."),
    (4, 4.5, "Kids loved it, ferry ride there is half the fun."),
    (4, 4.0, "A bit pricey but well maintained enclosures."),
    (5, 3.5, "Nice atmosphere but stalls repeat most weekends."),
    (6, 5.0, "Best duck I've had outside of Hong Kong."),
    (7, 4.0, "Good meeting point, gets very busy during events."),
    (8, 5.0, "Guide had amazing stories about the artists."),
    (9, 4.5, "Loud and fun, book ahead on weekends."),
    (10, 5.0, "Peaceful escape from the city, free entry is a bonus."),
    (11, 4.0, "Great for breakfast, arrive before 9am for parking."),
    (12, 5.0, "Long day but the Twelve Apostles views are unforgettable."),
]


def seed():
    ensure_schema()
    conn = get_connection()
    try:
        existing = conn.execute("SELECT COUNT(*) FROM attractions").fetchone()[0]
        if existing > 0:
            print(f"Attractions table already has {existing} rows, skipping seed.")
            return

        conn.executemany(
            "INSERT INTO attractions (name, category, description, rating) VALUES (?, ?, ?, ?)",
            ATTRACTIONS,
        )
        conn.executemany(
            "INSERT INTO reviews (attraction_id, rating, comment) VALUES (?, ?, ?)",
            REVIEWS,
        )
        conn.commit()
        print(f"Seeded {len(ATTRACTIONS)} attractions and {len(REVIEWS)} reviews.")
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
