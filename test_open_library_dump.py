import gzip
import json
import time
import string

def normalize(text):
    """Lowercase and remove punctuation for better matching."""
    if not text:
        return ""
    return text.translate(str.maketrans('', '', string.punctuation)).strip().lower()

def get_match_substring(input_norm):
    x = len(input_norm)
    if x <= 40:
        print(f"Using 100% of input string for matching ({x} characters).")
        return input_norm
    # Always take at least the first 40 chars, extend to end of word
    end = 40
    while end < x and input_norm[end].isalnum():
        end += 1
    base = input_norm[:end]
    remaining = input_norm[end:]
    remaining_len = len(remaining)
    # Apply the formula for y
    if x > 40:
        y = (1/150000) * x**2 - 0.003 * x + 1.0333
        y = max(min(y, 1.0), 0.6)  # Clamp between 0.6 and 1.0 for safety
    else:
        y = 1.0
    extra_chars = int(remaining_len * y)
    percent_used = ((len(base) + extra_chars) / x) * 100
    print(f"Using {percent_used:.1f}% of input string for matching ({len(base) + extra_chars} of {x} characters).")
    return base + remaining[:extra_chars]

def find_best_title_match(
    input_title,
    dump_path="data/ol_dump_editions_latest.txt.gz",
    max_results=5
):
    start_time = time.time()
    input_norm_full = normalize(input_title)
    input_norm = get_match_substring(input_norm_full)
    matches = []

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
                lccn = ", ".join(lccn) if isinstance(lccn, list) else lccn
                oclc = ", ".join(oclc) if isinstance(oclc, list) else oclc
                oclc_numbers = ", ".join(oclc_numbers) if isinstance(oclc_numbers, list) else oclc_numbers

                title_norm = normalize(title)
                full_title_norm = normalize(full_title)

                # Exact substring match (case-insensitive, punctuation-insensitive)
                if input_norm in title_norm or input_norm in full_title_norm:
                    # Only count as a match if at least one identifier is present
                    if lccn or oclc or oclc_numbers:
                        matches.append({
                            "title": title,
                            "full_title": full_title,
                            "display_title": full_title if full_title else title,
                            "lccn": lccn,
                            "oclc": oclc,
                            "oclc_numbers": oclc_numbers,
                            "record": record,
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
            print(f"  full_title: {match.get('full_title', '')}")
            print(f"  title: {match.get('title', '')}")
            print(f"  Title (display): {match['display_title']}")
            print(f"  LCCN: {match['lccn']}")
            print(f"  OCLC: {match['oclc']}")
            print(f"  OCLC Numbers: {match['oclc_numbers']}")
            print(f"  Full record: {json.dumps(match['record'], ensure_ascii=False, indent=2)}")
    else:
        print("No matches found.")

if __name__ == "__main__":
    input_title = input("Enter a book title to search for: ").strip()
    if input_title.startswith('"') and input_title.endswith('"'):
        input_title = input_title[1:-1]
    find_best_title_match(input_title)