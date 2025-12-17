import os
import argparse
from datetime import datetime

TS_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
]

HEADER_LINES = 4


def parse_ts(text):
    text = text.strip().strip('"')
    for fmt in TS_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    return None


def get_start_end(path):
    with open(path, "r", errors="ignore") as f:
        lines = f.readlines()

    start = None
    end = None

    # find start (after header)
    for ln in lines[HEADER_LINES:]:
        if not ln.strip():
            continue
        ts = parse_ts(ln.split(",")[0])
        if ts:
            start = ts
            break

    # find end (scan backwards)
    for ln in reversed(lines):
        if not ln.strip():
            continue
        ts = parse_ts(ln.split(",")[0])
        if ts:
            end = ts
            break

    return start, end


def detect_type(name):
    TYPES = [
        "TableDay",
        "TableETHour",
        "TableHour",
        "SYNOP",
        "Table10m",
        "TableSolarCharger10m",
    ]
    for t in TYPES:
        if t in name:
            return t
    return "Unknown"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--src", required=True, help="Station folder path")
    args = p.parse_args()

    files = [
        f for f in os.listdir(args.src)
        if f.endswith(".dat")
    ]

    if not files:
        print("❌ No .dat files found")
        return

    print(f"\n📂 Scanning station folder: {args.src}\n")

    for fname in sorted(files):
        path = os.path.join(args.src, fname)
        ftype = detect_type(fname)

        start, end = get_start_end(path)

        print(f"{ftype}")
        print(f"  File : {fname}")

        if start and end:
            print(f"  Start: {start}")
            print(f"  End  : {end}")
        else:
            print("  ❌ Could not detect timestamps")

        print()


if __name__ == "__main__":
    main()
