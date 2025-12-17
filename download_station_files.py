import argparse
import requests
import os

API_BASE = "http://192.168.0.65:3000/api"

def main():
    parser = argparse.ArgumentParser(
        description="Download all files for a given station from the API"
    )
    parser.add_argument(
        "station",
        help="Station name or code (e.g. ST31, Masaiti, Lukulu)"
    )
    parser.add_argument(
        "folder",
        help="Destination folder name (e.g. Lukulu)"
    )

    args = parser.parse_args()
    station = args.station
    folder = args.folder

    # ---------------- Fetch file list ----------------
    try:
        response = requests.get(f"{API_BASE}/files")
        response.raise_for_status()
        data = response.json()
        files = data.get("files", [])
    except requests.RequestException as e:
        print(f"❌ Error fetching file list: {e}")
        return

    # ---------------- Filter station files ----------------
    # station_files = [
    #     f["name"]
    #     for f in files
    #     if station in f["name"]
    # ]



    station_lower = station.lower()

    station_files = [
    f["name"]
    for f in files
    if station_lower in f["name"].lower()
]




    if not station_files:
        print(f"⚠️ No files found for station '{station}'")
        return

    # ---------------- Create destination folder ----------------
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError as e:
        print(f"❌ Error creating folder '{folder}': {e}")
        return

    # ---------------- Download files ----------------
    print(f"\n📥 Downloading {len(station_files)} files for station '{station}'\n")

    for filename in station_files:
        download_file(filename, folder)

    print("\n✅ Download complete")


def download_file(filename, dest_dir):
    url = f"{API_BASE}/download/{filename}"
    dest_path = os.path.join(dest_dir, filename)

    try:
        response = requests.get(url)
        response.raise_for_status()

        with open(dest_path, "wb") as f:
            f.write(response.content)

        print(f"✔ {filename}")

    except requests.RequestException as e:
        print(f"❌ Download failed: {filename} → {e}")
    except IOError as e:
        print(f"❌ File write error: {filename} → {e}")


if __name__ == "__main__":
    main()
