import gzip
import json
import time
import string
from rapidfuzz import fuzz

def normalize(text):
    """Lowercase and remove punctuation for better matching."""
    if not text:
        return ""
    return text.translate(str.maketrans('', '', string.punctuation)).strip().lower()

def get_input_ninety(input_norm):
    ninety_pct_len = int(len(input_norm) * 0.9)
    if ninety_pct_len >= len(input_norm):
        return input_norm
    # Extend to the end of the current word
    end = ninety_pct_len
    while end < len(input_norm) and input_norm[end].isalnum():
        end += 1
    return input_norm[:end]

def find_best_title_match(
    input_title,
    dump_path="data/ol_dump_editions_latest.txt.gz",
    threshold=96,  # >95
    max_results=5
):
    start_time = time.time()
    input_norm = normalize(input_title)
    matches = []

    # Use only the first 90% of the normalized input for matching, extended to word boundary
    input_ninety = get_input_ninety(input_norm)

    with gzip.open(dump_path, "rt", encoding="utf-8") as f:
        for line_num, line in enumerate(f):
            try:
                # Split line on tabs and parse only the last field as JSON
                fields = line.rstrip("\n").split("\t")
                if not fields or not fields[-1].startswith("{"):
                    continue  # skip malformed lines
                record = json.loads(fields[-1])
                title = record.get("title", "")
                full_title = record.get("full_title", "")
                subtitle = record.get("subtitle", "")
                lccn = record.get("lccn")
                oclc = record.get("oclc")
                oclc_numbers = record.get("oclc_numbers")
                lccn = ", ".join(lccn) if isinstance(lccn, list) else lccn
                oclc = ", ".join(oclc) if isinstance(oclc, list) else oclc
                oclc_numbers = ", ".join(oclc_numbers) if isinstance(oclc_numbers, list) else oclc_numbers

                title_norm = normalize(title)
                full_title_norm = normalize(full_title)

                # Substring match using first 90% of input, with even stricter checks
                input_word_count = len(input_norm.split())
                title_word_count = len(title_norm.split())
                min_word_count = max(3, input_word_count)
                if (
                    input_ninety
                    and len(title_norm) >= len(input_norm)
                    and (input_ninety in title_norm or input_ninety in full_title_norm)
                    and title_word_count >= min_word_count
                    and title_norm.strip()  # skip empty/whitespace titles
                ):
                    best_score = 100
                    display_title = full_title if full_title else title
                    if subtitle and not full_title:
                        display_title = f"{title} {subtitle}"
                    matches.append({
                        "score": best_score,
                        "display_title": display_title,
                        "lccn": lccn,
                        "oclc": oclc,
                        "oclc_numbers": oclc_numbers,
                    })
                    if len(matches) >= max_results:
                        break
                    continue

                # Fuzzy match using first 90% of input
                score_title = fuzz.partial_ratio(input_ninety, title_norm) if title_norm else 0
                score_full_title = fuzz.partial_ratio(input_ninety, full_title_norm) if full_title_norm else 0

                best_score = max(score_title, score_full_title)
                if best_score > 95:
                    display_title = full_title if score_full_title >= score_title and full_title else title
                    if subtitle and display_title == title:
                        display_title = f"{title} {subtitle}"
                    matches.append({
                        "score": best_score,
                        "display_title": display_title,
                        "lccn": lccn,
                        "oclc": oclc,
                        "oclc_numbers": oclc_numbers,
                    })
                    if len(matches) >= max_results:
                        break

            except Exception:
                continue

    elapsed = time.time() - start_time

    print(f"\nSearch completed in {elapsed:.2f} seconds.")
    if matches:
        for i, match in enumerate(matches, 1):
            print(f"\nMatch {i}:")
            print(f"  Score: {match['score']}")
            print(f"  Title: {match['display_title']}")
            print(f"  LCCN: {match['lccn']}")
            print(f"  OCLC: {match['oclc']}")
            print(f"  OCLC Numbers: {match['oclc_numbers']}")
    else:
        print("No matches found.")

if __name__ == "__main__":
    input_title = input("Enter a book title to search for: ").strip()
    if input_title.startswith('"') and input_title.endswith('"'):
        input_title = input_title[1:-1]
    find_best_title_match(input_title)