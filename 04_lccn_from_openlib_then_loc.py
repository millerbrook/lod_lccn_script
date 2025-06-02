# filepath: c:\Users\ch738340\OneDrive - University of Central Florida\Documents\CHDR\PRINT Project\data exploration\lccn script\04_lccn_from_openlib_then_loc.py
import time
import os
import json
import csv
import concurrent.futures

from get_lccn_from_title import get_lccn_from_title
from retrieve_from_open_library_dump import find_best_title_match

def read_titles(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def normalize(text):
    import string
    if not text:
        return ""
    return text.translate(str.maketrans('', '', string.punctuation)).strip().lower()

def title_in_csv(title, csv_path):
    """Check if a (normalized) title is already in the CSV."""
    if not os.path.isfile(csv_path):
        return False
    norm_title = normalize(title)
    with open(csv_path, "r", encoding="utf-8", newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            existing_title = row.get("Title", "")
            if normalize(existing_title) == norm_title:
                return True
    return False

def append_results_to_csv(results, csv_path):
    fieldnames = ["Title", "LCCN", "Alt_LCCN", "OCLC", "Alt_OCLC", "Source"]
    file_exists = os.path.isfile(csv_path)
    with open(csv_path, "a", newline='', encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists or os.stat(csv_path).st_size == 0:
            writer.writeheader()
        for res in results:
            writer.writerow({
                "Title": res["title"],
                "LCCN": res.get("lccn", "n/a"),
                "Alt_LCCN": repr(res.get("alt_lccn", [])),
                "OCLC": res.get("oclc", "n/a"),
                "Alt_OCLC": repr(res.get("alt_oclc", [])),
                "Source": res.get("source", "None")
            })

def get_lccn_with_timeout(title, timeout=10):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(get_lccn_from_title, title)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            print("LOC search took too long (>10s), moving to Open Library...")
            return None

def main():
    titles = read_titles(os.path.join("data", "unique_sources.txt"))  # <-- updated filename here
    csv_path = os.path.join("data", "titles_lccn.csv")
    results = []
    for idx, title in enumerate(titles, 1):
        if title_in_csv(title, csv_path):
            print(f"[{idx}/{len(titles)}] Skipping '{title}' (already in titles_lccn.csv)")
            continue
        print(f"\n[{idx}/{len(titles)}] Searching LOC for: {title}")

        loc_result = get_lccn_with_timeout(title, timeout=10)

        if loc_result and loc_result.get("lccn") and loc_result["lccn"] != 'n/a':
            print(f"LOC LCCN found: {loc_result['lccn']}")
            results.append({"title": title, "source": "LOC", **loc_result})
        else:
            print("No LCCN from LOC, searching Open Library...")
            openlib_result = find_best_title_match(title)
            if openlib_result and openlib_result.get("LCCN") and openlib_result["LCCN"] not in ('', 'n/a'):
                print(f"Open Library LCCN found: {openlib_result['LCCN']}")
                results.append({
                    "title": title,
                    "source": "OpenLibrary",
                    "lccn": openlib_result.get("LCCN", "n/a"),
                    "alt_lccn": openlib_result.get("Alt_LCCN", []),
                    "oclc": openlib_result.get("OCLC", "n/a"),
                    "alt_oclc": openlib_result.get("Alt_OCLC", [])
                })
            else:
                print("No LCCN found in either source.")
                results.append({"title": title, "source": "None", "lccn": "n/a", "alt_lccn": [], "oclc": "n/a", "alt_oclc": []})
        time.sleep(10)

    # Save results to JSON
    os.makedirs("data", exist_ok=True)
    with open("data/lccn_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Append results to CSV
    append_results_to_csv(results, csv_path)

if __name__ == "__main__":
    main()