"""Creates the attractions/reviews tables if they don't already exist.

Run directly: `python init_db.py`
Also called automatically on service startup by app.py, so a fresh
container always has a usable schema even if this script wasn't run
as a separate init step.
"""

from db import ensure_schema

if __name__ == "__main__":
    ensure_schema()
    print("Schema ensured.")
