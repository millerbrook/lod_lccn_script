import requests
import sys

def search_loc_books(title):
    url = "https://www.loc.gov/books/"
    params = {
        "q": title,
        "fo": "json"
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scriptname.py \"Book Title Here\"")
        sys.exit(1)
    query_title = " ".join(sys.argv[1:]).strip()
    data = search_loc_books(query_title)
    results = data.get("results", [])
    for record in results:
        record_title = record.get("title", "")
        # Compare the start of the returned title to the query (case-insensitive, stripped)
        if record_title.strip().lower().startswith(query_title.lower()):
            lccn_list = record.get("number_lccn", [])
            if isinstance(lccn_list, list):
                if len(lccn_list) == 1:
                    print("Title:", record_title)
                    print("number_lccn:", lccn_list[0])
                elif len(lccn_list) > 1:
                    print("Title:", record_title)
                    print("number_lccn:", lccn_list)
                else:
                    print("Title:", record_title)
                    print("number_lccn: N/A")
            else:
                print("Title:", record_title)
                print("number_lccn: N/A")