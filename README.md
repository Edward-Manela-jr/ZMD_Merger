# Weather Station DAT Tools

Python utilities for working with meteorological `.dat` files.

## Scripts

### merge_dat_simple.py
Merges primary (ZMD) and secondary station `.dat` files after verifying timestamp continuity.

### scan_station_dates.py
Scans individual station `.dat` files and reports start and end timestamps for each table type.

## Usage

```bash
python merge_dat_simple.py --src "path/to/station" --dst "path/to/output" --dry-run
remove --dry-run to merge
python scan_station_dates.py --src "path/to/station"
