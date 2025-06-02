import requests
import os
import json
from rapidfuzz import fuzz
import re

def get_lccn_from_title(title):
    url = "https://www.loc.gov/search/"
    params = {
        "q": title,
        "fo": "json",
        "count": 100,  # Adjust count as needed
        'fa': 'original-format:book',
    }
    #print(f"DEBUG URL: {url} with params: {params}")  # Print the URL and params for debugging
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        # Debug: Write the full JSON response
        os.makedirs("data", exist_ok=True)
        with open("data/debug-data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        results = data.get("results", [])

        threshold = 80
        matches = []
        input_len = len(title.strip())
        for record in results:
            candidate_titles = []
            if "title" in record and isinstance(record["title"], str):
                candidate_titles.append(record["title"])
            if isinstance(record.get("item"), dict) and "title" in record["item"]:
                candidate_titles.append(record["item"]["title"])

            record_lccn = record.get("number_lccn", [])
            record_oclc = record.get("number_oclc", [])

            for candidate_title in candidate_titles:
                #print(f"DEBUG candidate title: '{candidate_title}'")
                norm_input = normalize(title)
                norm_candidate = normalize(candidate_title)
                # Print normalized strings for debugging
                #print(f"DEBUG norm_input: '{norm_input}', norm_candidate: '{norm_candidate}'")
                # Compare input to the start of the normalized candidate title
                score = fuzz.ratio(norm_input, norm_candidate[:len(norm_input)])
                #print(f"DEBUG score for '{candidate_title}': {score}")
                if score >= threshold:
                    matches.append({
                        "score": score,
                        "title": candidate_title,
                        "number_lccn": record_lccn,
                        "number_oclc": record_oclc
                    })

        if matches:
            # Sort matches by score descending
            matches.sort(key=lambda x: x["score"], reverse=True)
            #print("DEBUG: All matches and their LCCNs:")
            #for m in matches:
                #print(f"  Title: {m['title']}, LCCN: {m['number_lccn']}, Score: {m['score']}")
            best = matches[0]
            alt_lccn = []
            alt_oclc = []
            # Collect alternate LCCNs/OCLCs from other matches
            for m in matches[1:]:
                alt_lccn.extend([l for l in m.get("number_lccn", []) if l not in alt_lccn and l not in best.get("number_lccn", [])])
                alt_oclc.extend([o for o in m.get("number_oclc", []) if o not in alt_oclc and o not in best.get("number_oclc", [])])
            lccn_list = best.get("number_lccn", [])
            oclc_list = best.get("number_oclc", [])
            lccn = lccn_list[0] if lccn_list else 'n/a'
            oclc = oclc_list[0] if oclc_list else 'n/a'
            return {
                "lccn": lccn,
                "alt_lccn": alt_lccn,
                "oclc": oclc,
                "alt_oclc": alt_oclc
            }
        return {
            "lccn": 'n/a',
            "alt_lccn": [],
            "oclc": 'n/a',
            "alt_oclc": []
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            "lccn": 'n/a',
            "alt_lccn": [],
            "oclc": 'n/a',
            "alt_oclc": []
        }

def normalize(s):
    # Lowercase, remove punctuation, collapse whitespace
    return re.sub(r'\W+', '', s.strip().lower())

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python test2_get_lccn_from_title.py \"Book Title Here\"")
        sys.exit(1)
    title = " ".join(sys.argv[1:])
    result = get_lccn_from_title(title)
    print(f"LCCN: {result['lccn']}")
    print(f"Alt LCCN: {result['alt_lccn']}")
    print(f"OCLC: {result['oclc']}")
    print(f"Alt OCLC: {result['alt_oclc']}")