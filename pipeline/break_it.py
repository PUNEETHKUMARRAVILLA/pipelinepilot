"""Inject a realistic failure into the raw file, so the agent has something to investigate.

Run:  python -m pipeline.break_it <scenario>
      python -m pipeline.break_it reset      (back to clean data)

Scenarios: schema_drift, null_spike, duplicates, stale_data, type_change, volume_drop
"""
import csv
import json
import random
import sys
from datetime import datetime, timedelta

from pipeline.config import INJECTED, LAST_FAILURE, RAW_FILE
from pipeline.generate_data import generate

SCENARIOS = {
    "schema_drift": "Upstream renamed column fare_amount to fare",
    "null_spike": "About 40% of pickup_zone values arrive empty",
    "duplicates": "The same batch of rows was delivered twice",
    "stale_data": "Source sent a 3-day-old extract instead of today's",
    "type_change": "fare_amount now arrives as text with a $ sign",
    "volume_drop": "Only about 3% of the usual rows arrived",
}


def _read():
    with open(RAW_FILE, newline="") as f:
        rows = list(csv.reader(f))
    return rows[0], rows[1:]


def _write(header, rows):
    with open(RAW_FILE, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def inject(scenario: str):
    generate()  # always start from clean data, one failure at a time
    header, rows = _read()
    rng = random.Random(7)
    col = {name: i for i, name in enumerate(header)}

    if scenario == "schema_drift":
        header[col["fare_amount"]] = "fare"
    elif scenario == "null_spike":
        for r in rows:
            if rng.random() < 0.4:
                r[col["pickup_zone"]] = ""
    elif scenario == "duplicates":
        rows = rows + rows[:800]
    elif scenario == "stale_data":
        for r in rows:
            for c in ("pickup_ts", "dropoff_ts"):
                ts = datetime.fromisoformat(r[col[c]]) - timedelta(days=3)
                r[col[c]] = ts.isoformat(sep=" ")
    elif scenario == "type_change":
        for r in rows:
            r[col["fare_amount"]] = f"${r[col['fare_amount']]}"
    elif scenario == "volume_drop":
        rows = rows[: max(1, len(rows) * 3 // 100)]
    else:
        raise SystemExit(f"Unknown scenario '{scenario}'. Choose from: {', '.join(SCENARIOS)} or reset")

    _write(header, rows)
    INJECTED.write_text(json.dumps({"scenario": scenario, "truth": SCENARIOS[scenario],
                                    "injected_at": datetime.now().isoformat()}, indent=2))
    print(f"Injected '{scenario}': {SCENARIOS[scenario]}")
    print("Next: python -m pipeline.run")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    if sys.argv[1] == "reset":
        generate()
        INJECTED.unlink(missing_ok=True)
        LAST_FAILURE.unlink(missing_ok=True)  # the old failure no longer matches the data
        print("Raw data reset to clean.")
    else:
        inject(sys.argv[1])
