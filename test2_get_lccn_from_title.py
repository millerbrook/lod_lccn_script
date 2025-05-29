import requests
import os
import json

def get_lccn_from_title(title):
    url = "https://www.loc.gov/search/"
    params = {
        "q": title,
        "fo": "json",
        "count": 100,  # Adjust count as needed
    }
    print(f"DEBUG URL: {url} with params: {params}")  # Print the URL and params for debugging
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        # Debug: Write the full JSON response
        os.makedirs("data", exist_ok=True)
        with open("data/debug-data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        results = data.get("results", [])
        #print(json.dumps(results, indent=2, ensure_ascii=False))  # Print the results for debugging
        for record in results:
            record_title = record.get("title", "")
            #print(f"DEBUG Record Title: {title}: {record_title}")  # Print each record title for debugging
            if record_title.strip().lower().startswith(title.strip().lower()):
                lccn_list = record.get("number_lccn", [])
                if not isinstance(lccn_list, list):
                    lccn_list = []
                lccn = lccn_list[0] if lccn_list else 'n/a'
                alt_lccn = lccn_list[1:] if len(lccn_list) > 1 else []

                oclc_list = record.get("number_oclc", [])
                if not isinstance(oclc_list, list):
                    oclc_list = []
                oclc = oclc_list[0] if oclc_list else 'n/a'
                alt_oclc = oclc_list[1:] if len(oclc_list) > 1 else []

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