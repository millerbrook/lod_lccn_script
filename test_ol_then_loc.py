import sys
import pprint

# Import the Open Library and LOC functions
from retrieve_from_open_library_dump import find_best_title_match
from get_lccn_from_title import get_lccn_from_title  # You need to rename your function in test2_get_lccn_from_title.py

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_ol_then_loc.py \"Book Title Here\"")
        sys.exit(1)
    input_title = " ".join(sys.argv[1:]).strip()

    # Query Open Library
    result = find_best_title_match(input_title)

    # If LCCN found, print result and script name
    if result.get("LCCN"):
        pprint.pprint(result)
        print("retrieve_from_open_library_dump.py")
    else:
        # Try LOC
        title_for_loc = result.get("Title", input_title)
        lccn = get_lccn_from_title(title_for_loc)
        if lccn and lccn != 'n/a':
            result["LCCN"] = lccn
            pprint.pprint(result)
            print("The lccn value was obtained through LOC")
        else:
            pprint.pprint(result)
            print("No LCCN found in Open Library or LOC")