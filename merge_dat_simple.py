"""To perform a dry run, use this command:
python merge_dat_simple.py --src "E:/MERGE/Nkeyema" --dst "E:/MERGE/MergedOutput" --dry-run

replace the paths with your actual source and destination directories.

"""


import tkinter as tk
import os
import argparse
from datetime import datetime, timedelta

tk.Tk().withdraw()  # we don't want a full GUI, so keep the root window from appearing
#gui using tkinter to select folders
tk.Tk().withdraw()  # we don't want a full GUI, so keep the root window from appearing  


TS_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
]

FREQ_MAP = {
    "TableDay": timedelta(days=1),
    "TableETHour": timedelta(hours=1),
    "TableHour": timedelta(hours=1),
    "SYNOP": timedelta(hours=1),
    "Table10m": timedelta(minutes=10),
    "TableSolarCharger10m": timedelta(minutes=10),
}


def parse_ts(text):
    text = text.strip().strip('"')
    for fmt in TS_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def find_last_timestamp(lines):
    for ln in reversed(lines):
        if not ln.strip():
            continue
        parts = ln.split(",")
        ts = parse_ts(parts[0])
        if ts:
            return ts
    return None


def find_first_timestamp_after_header(lines, header_lines=4):
    for ln in lines[header_lines:]:
        if not ln.strip():
            continue
        parts = ln.split(",")
        ts = parse_ts(parts[0])
        if ts:
            return ts
    return None


def detect_suffix(name):
    for k in FREQ_MAP:
        if k in name:
            return k
    return None


def merge_pair(a_file, b_file, dst, dry):
    with open(a_file, "r", errors="ignore") as f:
        A = f.readlines()

    with open(b_file, "r", errors="ignore") as f:
        B = f.readlines()

    suf = detect_suffix(a_file)
    if not suf:
        print(f"  ❌ Cannot detect frequency from filename")
        return

    delta = FREQ_MAP[suf]

    last_A = find_last_timestamp(A)
    first_B = find_first_timestamp_after_header(B)

    if last_A is None:
        print(f"  ❌ No timestamp found in A → {a_file}")
        return

    if first_B is None:
        print(f"  ❌ No timestamp found in B → {b_file}")
        return

    expected = last_A + delta

    print(f"  Last A   = {last_A}")
    print(f"  First B = {first_B}")
    print(f"  Expected= {expected}")

    if first_B != expected:
        print("  ❌ Continuity check failed → skipping")
        return

    print("  ✅ Continuity OK — ready to merge")

    if dry:
        print("  (dry-run) Not writing file.")
        return

    os.makedirs(dst, exist_ok=True)
    out = os.path.join(dst, os.path.basename(b_file))

    with open(out, "w") as f:
        f.writelines(B[:4])  # header from B

        for ln in A:
            parts = ln.split(",")
            if parse_ts(parts[0]):
                f.write(ln)

        for ln in B[4:]:
            parts = ln.split(",")
            if parse_ts(parts[0]):
                f.write(ln)

    print(f"  ✅ Wrote merged → {out}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True)
    parser.add_argument("--dst", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    files = [
        os.path.join(args.src, f)
        for f in os.listdir(args.src)
        if f.endswith(".dat")
    ]

    # for suf in FREQ_MAP:
    #     A = [f for f in files if "ZMD" in f and suf in f]
    #     B = [f for f in files if "Secondary" in f and suf in f]

    #     if len(A) == 1 and len(B) == 1:
    #         print("\nChecking pair:")
    #         print("  A:", A[0])
    #         print("  B:", B[0])
    #         merge_pair(A[0], B[0], args.dst, args.dry_run)



    for suf in FREQ_MAP:
        A = [f for f in files if "ZMD" in os.path.basename(f) and suf in f]
        B = [f for f in files if "ZMD" not in os.path.basename(f) and suf in f]

        if len(A) == 1 and len(B) == 1:
            print("\nChecking pair:")
            print("  A:", A[0])
            print("  B:", B[0])
            merge_pair(A[0], B[0], args.dst, args.dry_run)


if __name__ == "__main__":
    main()
