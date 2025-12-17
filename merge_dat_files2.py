#!/usr/bin/env python3
"""
merge_dat_files_final.py

Creates one merged file per valid pair (ZMD -> Secondary).
Header is taken from the SECOND file and written once at the top.

Usage (dry-run first):
  python merge_dat_files_final.py --src "E:/MERGE/Nkeyema" --dst "E:/MERGE/MergedOutput" --dry-run

Then run for real:
  python merge_dat_files_final.py --src "E:/MERGE/Nkeyema" --dst "E:/MERGE/MergedOutput"
"""

import os
import re
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")

# Expected frequencies (suffix -> timedelta)
FREQ_MAP = {
    "TableDay": timedelta(days=1),
    "TableETHour": timedelta(hours=1),
    "TableHour": timedelta(hours=1),
    "SYNOP": timedelta(hours=1),
    "TableSolarCharger10m": timedelta(minutes=10),
    "Table10m": timedelta(minutes=10),
}

# Timestamp regex: match "M/D/YYYY H:MM" or "MM/DD/YYYY HH:MM" optionally with seconds
TS_REGEX = re.compile(r"^\s*(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}(?::\d{2})?)")

# Common timestamp formats to try when parsing
TS_FORMATS = ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M")


# ---------- helpers ----------
def read_lines(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.readlines()


def try_parse_ts(txt):
    """Return datetime or raise ValueError."""
    for fmt in TS_FORMATS:
        try:
            return datetime.strptime(txt, fmt)
        except ValueError:
            continue
    # if none match, raise
    raise ValueError(f"Unknown timestamp format: {txt!r}")


def find_first_data_index(lines):
    for i, ln in enumerate(lines):
        clean = (
            ln.replace("\ufeff", "")             # remove BOM
              .replace("\xa0", " ")             # non-breaking space
              .replace("\t", " ")               # tabs → normal spaces
        )
        clean = re.sub(r"\s+", " ", clean).strip()  # collapse whitespace

        m = TS_REGEX.match(clean)
        if m:
            # verify timestamp parses
            ts_str = m.group(1)
            try:
                try_parse_ts(ts_str)
                return i
            except ValueError:
                continue
    return None


def get_first_last_ts_from_lines(lines):
    """
    Return tuple: (first_data_index, first_ts (datetime), last_ts (datetime), data_lines_list)
    If no data rows found, returns (None, None, None, []).
    """
    idx = find_first_data_index(lines)
    if idx is None:
        return None, None, None, []

    data_lines = [ln.rstrip("\n") for ln in lines[idx:] if ln.strip() != ""]
    # first ts
    m = TS_REGEX.match(data_lines[0])
    first_ts = try_parse_ts(m.group(1)) if m else None

    # last ts
    last_ts = None
    for ln in reversed(data_lines):
        m = TS_REGEX.match(ln)
        if m:
            try:
                last_ts = try_parse_ts(m.group(1))
                break
            except ValueError:
                continue

    return idx, first_ts, last_ts, data_lines


def get_suffix_from_name(name):
    base = os.path.basename(name)
    for suf in FREQ_MAP.keys():
        if suf in base:
            return suf
    return None


# ---------- pairing ----------
def pair_files_in_folder(src_folder):
    """
    Pair by suffix. For each suffix in FREQ_MAP we look for a ZMD file and a SECONDARY file.
    Returns list of (zmd_path, secondary_path).
    """
    all_files = [
        os.path.join(src_folder, f)
        for f in os.listdir(src_folder)
        if f.lower().endswith(".dat") and os.path.isfile(os.path.join(src_folder, f))
    ]

    pairs = []
    for suf in FREQ_MAP.keys():
        zmd = None
        sec = None
        for f in all_files:
            fn = os.path.basename(f).upper()
            if suf.upper() in fn:
                if "ZMD" in fn:
                    zmd = f
                elif "SECONDARY" in fn:
                    sec = f
        if zmd and sec:
            pairs.append((zmd, sec))
    return pairs


# ---------- merge logic ----------
def merge_pair(zmd_file, sec_file, dst_folder, dry_run=False):
    logging.info(f"\nChecking pair:\n  A: {zmd_file}\n  B: {sec_file}")

    lines_a = read_lines(zmd_file)
    lines_b = read_lines(sec_file)

    idx_a, first_a, last_a, data_a = get_first_last_ts_from_lines(lines_a)
    idx_b, first_b, last_b, data_b = get_first_last_ts_from_lines(lines_b)

    if idx_a is None:
        logging.warning(f"  ❌ No data rows found in {os.path.basename(zmd_file)} — skipping.")
        return False
    if idx_b is None:
        logging.warning(f"  ❌ No data rows found in {os.path.basename(sec_file)} — skipping.")
        return False

    suffix = get_suffix_from_name(sec_file)
    if suffix is None or suffix not in FREQ_MAP:
        logging.warning(f"  ⚠ Unknown or missing suffix for {os.path.basename(sec_file)} — skipping.")
        return False

    delta = FREQ_MAP[suffix]
    expected_next = last_a + delta

    logging.info(f"  Last A:   {last_a}")
    logging.info(f"  First B:  {first_b}")
    logging.info(f"  Expected: {expected_next}")

    if first_b != expected_next:
        logging.warning("  ❌ CONTINUITY FAILED — timestamps do not line up.")
        if first_b > expected_next:
            # compute missing count
            t = expected_next
            missing = 0
            while t < first_b:
                missing += 1
                t += delta
            logging.info(f"   → Missing {missing} interval(s) (from {expected_next} to {first_b - delta})")
        else:
            logging.info("   → B starts earlier than expected (overlap).")
        return False

    # Continuity OK — merge with header from SECOND file only once at top
    header_b = lines_b[:idx_b]
    merged_lines = []
    merged_lines.extend(header_b)                       # header once
    merged_lines.extend([ln + "\n" for ln in data_a])  # all data from A
    merged_lines.extend([ln + "\n" for ln in data_b])  # all data from B

    out_path = os.path.join(dst_folder, os.path.basename(sec_file))
    os.makedirs(dst_folder, exist_ok=True)

    if dry_run:
        logging.info(f"  (dry-run) Would write merged file: {out_path}")
    else:
        with open(out_path, "w", encoding="utf-8") as fo:
            fo.writelines(merged_lines)
        logging.info(f"  ✅ Wrote merged file: {out_path}")

    return True


# ---------- main ----------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True, help="Folder with .dat files (one station folder)")
    parser.add_argument("--dst", required=True, help="Destination folder for merged files")
    parser.add_argument("--dry-run", action="store_true", help="Do not write files; show what would happen")
    args = parser.parse_args()

    pairs = pair_files_in_folder(args.src)
    logging.info(f"Found {len(pairs)} pair(s) to check.")

    for zmd, sec in pairs:
        try:
            merge_pair(zmd, sec, args.dst, dry_run=args.dry_run)
        except Exception as e:
            logging.error(f"Error for pair {zmd} & {sec}: {e}")


if __name__ == "__main__":
    main()
