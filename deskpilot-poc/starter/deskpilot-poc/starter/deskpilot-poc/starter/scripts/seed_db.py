"""Create data/tickets.db and load the 30 seed tickets.

Run:  python scripts/seed_db.py          (keeps existing data)
      python scripts/seed_db.py --reset  (start again from the seed file)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import db

if __name__ == "__main__":
    count = db.init_db(reset="--reset" in sys.argv)
    print(f"Ticket store ready: {count} tickets in data/tickets.db")
