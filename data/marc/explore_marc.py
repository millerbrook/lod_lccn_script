import sys
from pymarc import MARCReader

def normalize(text):
    return text.lower().strip() if text else ""

if len(sys.argv) < 2:
    print("Usage: python explore_marc.py \"Title to search for\"")
    sys.exit(1)

search_title = normalize(sys.argv[1])

with open('BooksAll.2016.combined.utf8', 'rb') as fh:
    reader = MARCReader(fh, to_unicode=True, force_utf8=True)
    found = False
    for i, record in enumerate(reader):
        if record is None:
            continue  # skip invalid records
        title = record.title if record.title else "No title"
        author = record.author if record.author else "No author"
        lccn = "No LCCN"
        if record['010'] and 'a' in record['010']:
            lccn = record['010']['a']
        if normalize(title) == search_title:
            print(f"Record {i+1}:")
            print(f"  Title: {title}")
            print(f"  Author: {author}")
            print(f"  LCCN: {lccn}")
            print()
            found = True
    if not found:
        print(f"No records found with title: {search_title}")