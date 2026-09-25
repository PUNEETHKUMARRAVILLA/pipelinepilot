"""Create a clean, realistic-looking raw file of taxi trips for the last 24 hours.

Run:  python -m pipeline.generate_data
Later you can swap this for real NYC TLC data (see README).
"""
import csv
import random
from datetime import datetime, timedelta

from pipeline.config import RAW_FILE

COLUMNS = [
    "trip_id", "pickup_ts", "dropoff_ts", "pickup_zone", "passenger_count",
    "trip_distance", "fare_amount", "tip_amount", "total_amount", "payment_type",
]
ZONES = ["Midtown", "Upper East Side", "JFK Airport", "LaGuardia", "Williamsburg",
         "Harlem", "SoHo", "Financial District", "Astoria", "Chelsea"]


def generate(n_rows: int = 5000, seed: int = 42) -> int:
    rng = random.Random(seed)
    now = datetime.now().replace(microsecond=0)
    with open(RAW_FILE, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for i in range(1, n_rows + 1):
            pickup = now - timedelta(minutes=rng.randint(0, 24 * 60))
            minutes = rng.randint(4, 55)
            distance = round(minutes * rng.uniform(0.15, 0.4), 2)
            fare = round(3 + distance * 2.5, 2)
            tip = round(fare * rng.choice([0, 0.1, 0.15, 0.2]), 2)
            w.writerow([
                i,
                pickup.isoformat(sep=" "),
                (pickup + timedelta(minutes=minutes)).isoformat(sep=" "),
                rng.choice(ZONES),
                rng.randint(1, 4),
                distance,
                fare,
                tip,
                round(fare + tip, 2),
                rng.choice(["card", "cash"]),
            ])
    return n_rows


if __name__ == "__main__":
    rows = generate()
    print(f"Wrote {rows} clean rows to {RAW_FILE}")
