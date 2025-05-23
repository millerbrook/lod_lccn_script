import gzip
import json
import time
import string
import csv
import os
from rapidfuzz import fuzz
import ast

def normalize(text):
    """Lowercase and remove punctuation for better matching."""
    if not text:
        return ""
    return text.translate(str.maketrans('', '', string.punctuation)).strip().lower()

def get_match_substring(input_norm):
    x = len(input_norm)
    if x <= 40:
        return input_norm
    # Always take at least the first 40 chars, extend to end of word
    end = 40
    while end < x and input_norm[end].isalnum():
        end += 1
    base = input_norm[:end]
    remaining = input_norm[end:]
    remaining_len = len(remaining)
    if x > 40:
        y = (1/150000) * x**2 - 0.003 * x + 1.0333
        y = max(min(y, 1.0), 0.6)
    else:
        y = 1.0
    extra_chars = int(remaining_len * y)
    return base + remaining[:extra_chars]

def is_reasonable_length(candidate, input_norm, factor=1.5):
    return len(candidate) >= len(input_norm) and len(candidate) <= factor * len(input_norm)

def find_best_title_match(
    input_title,
    dump_path="data/ol_dump_editions_latest.txt.gz",
    max_results=10
):
    start_time = time.time()
    input_norm_full = normalize(input_title)
    input_norm = get_match_substring(input_norm_full)
    matches = []
    max_perfect_matches = 3

    # CSV path and fieldnames
    csv_path = "data/titles_lccn.csv"
    fieldnames = ["Title", "LCCN", "Alt_LCCN", "OCLC", "Alt_OCLC", "No_match"]

    # Check if the title is already in the CSV (fuzzy match, >=95%)
    file_exists = os.path.isfile(csv_path)
    already_done = False
    existing_row = None
    if file_exists:
        with open(csv_path, "r", encoding="utf-8", newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                existing_title = row.get("Title", "").strip()
                existing_title_norm = normalize(existing_title)
                score = fuzz.partial_ratio(input_norm, existing_title_norm)
                if score >= 95:
                    already_done = True
                    existing_row = row
                    break

    if already_done:
        print("Search already done!")
        print("\nResult:")
        print(f"Title: {existing_row.get('Title','')}")
        print(f"LCCN: {existing_row.get('LCCN','')}")
        print(f"Alt_LCCN: {existing_row.get('Alt_LCCN','')}")
        print(f"OCLC: {existing_row.get('OCLC','')}")
        print(f"Alt_OCLC: {existing_row.get('Alt_OCLC','')}")
        print(f"No_match: {existing_row.get('No_match','')}")
        return existing_row

    # Search logic
    with gzip.open(dump_path, "rt", encoding="utf-8") as f:
        for line_num, line in enumerate(f):
            try:
                fields = line.rstrip("\n").split("\t")
                if not fields or not fields[-1].startswith("{"):
                    continue  # skip malformed lines
                record = json.loads(fields[-1])
                title = record.get("title", "")
                full_title = record.get("full_title", "")
                lccn = record.get("lccn")
                oclc = record.get("oclc")
                oclc_numbers = record.get("oclc_numbers")
                # Normalize to lists for easier handling
                lccn_list = lccn if isinstance(lccn, list) else ([lccn] if lccn else [])
                oclc_list = oclc if isinstance(oclc, list) else ([oclc] if oclc else [])
                oclc_numbers_list = oclc_numbers if isinstance(oclc_numbers, list) else ([oclc_numbers] if oclc_numbers else [])
                # Combine OCLC and OCLC_numbers, preserving order
                all_oclc = [str(x) for x in oclc_list + oclc_numbers_list if x]
                all_lccn = [str(x) for x in lccn_list if x]

                title_norm = normalize(title)
                full_title_norm = normalize(full_title)

                # Fuzzy substring match using RapidFuzz partial_ratio, threshold 98%
                score_title = fuzz.partial_ratio(input_norm, title_norm) if is_reasonable_length(title_norm, input_norm) else 0
                score_full_title = fuzz.partial_ratio(input_norm, full_title_norm) if is_reasonable_length(full_title_norm, input_norm) else 0

                min_substring_length = int(0.95 * len(input_norm))
                is_good_substring = (
                    (input_norm in title_norm and len(input_norm) >= min_substring_length) or
                    (input_norm in full_title_norm and len(input_norm) >= min_substring_length)
                )
                if is_good_substring and (score_title >= 96 or score_full_title >= 96):
                    if all_lccn or all_oclc:
                        matches.append({
                            "title": title,
                            "full_title": full_title,
                            "display_title": full_title if full_title else title,
                            "lccn": all_lccn,
                            "oclc": all_oclc,
                            "record": record,
                            "score": max(score_title, score_full_title),
                            "score_title": score_title,
                            "score_full_title": score_full_title,
                            "oclc_numbers": oclc_numbers,
                        })
                        if len(matches) >= max_perfect_matches:
                            break
            except Exception:
                continue

    elapsed = time.time() - start_time

    # Prepare CSV output
    best_lccn = ""
    alt_lccn = []
    best_oclc = ""
    alt_oclc = []
    no_match = ""

    if matches:
        # Flatten all LCCNs and OCLCs from all matches, preserving order and uniqueness
        all_lccns = []
        all_oclcs = []
        for match in matches:
            for l in match["lccn"]:
                if l and l not in all_lccns:
                    all_lccns.append(l)
            for o in match["oclc"]:
                if o and o not in all_oclcs:
                    all_oclcs.append(o)
        if all_lccns:
            best_lccn = all_lccns[0]
            alt_lccn = all_lccns[1:4]
        if all_oclcs:
            best_oclc = all_oclcs[0]
            alt_oclc = all_oclcs[1:4]
    else:
        no_match = "No match"

    # Ensure all alt_lccn values are strings (same type as best_lccn)
    alt_lccn = [str(x) for x in alt_lccn]
    alt_oclc = [str(x) for x in alt_oclc]

    # Write to CSV (append, never overwrite)
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    file_exists = os.path.isfile(csv_path)
    with open(csv_path, "a", newline='', encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists or os.stat(csv_path).st_size == 0:
            writer.writeheader()
        writer.writerow({
            "Title": input_title,
            "LCCN": best_lccn,
            "Alt_LCCN": repr(alt_lccn),
            "OCLC": best_oclc,
            "Alt_OCLC": repr(alt_oclc),
            "No_match": no_match
        })

    print(f"\nSearch completed in {elapsed:.2f} seconds.")
    if matches:
        print(f"Best LCCN: {best_lccn}")
        print(f"Alt LCCN: {alt_lccn}")
        print(f"Best OCLC: {best_oclc}")
        print(f"Alt OCLC: {alt_oclc}")
    else:
        print("No matches found.")

    if matches:
        for i, match in enumerate(matches, 1):
            print(f"\nMatch {i}:")
            print(f"  Score: {match.get('score', '')}")
            print(f"  score_title: {match.get('score_title', '')}")
            print(f"  score_full_title: {match.get('score_full_title', '')}")
            print(f"  full_title: {match.get('full_title', '')}")
            print(f"  title: {match.get('title', '')}")
            print(f"  Title (display): {match.get('display_title', '')}")
            print(f"  LCCN: {match.get('lccn', '')}")
            print(f"  OCLC: {match.get('oclc', '')}")
            print(f"  OCLC Numbers: {match.get('oclc_numbers', '')}")
            print(f"Full record:\n{json.dumps(match['record'], ensure_ascii=False, indent=2)}")
    else:
        print("No matches found.")

    # Return a summary dict for module use
    return {
        "Title": input_title,
        "LCCN": best_lccn,
        "Alt_LCCN": alt_lccn,
        "OCLC": best_oclc,
        "Alt_OCLC": alt_oclc,
        "No_match": no_match,
        "matches": matches
    }

if __name__ == "__main__":
    input_title = input("Enter a book title to search for: ").strip()
    if input_title.startswith('"') and input_title.endswith('"'):
        input_title = input_title[1:-1]
    find_best_title_match(input_title)