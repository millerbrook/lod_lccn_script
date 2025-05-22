Before running make, create and activate your virtual environment (e.g., python3 -m venv venv && source venv/bin/activate). All dependencies should be installed in the active environment.

## Downloading the Open Library Editions Data Dump

The script `test_open_library_dump.py` expects the Open Library editions data dump in gzipped format at `data/ol_dump_editions_latest.txt.gz`.

To download the latest dump, run:

```bash
mkdir -p data
wget https://openlibrary.org/data/ol_dump_editions_latest.txt.gz -O data/ol_dump_editions_latest.txt.gz
```

You can find more information and other dumps at:  
https://openlibrary.org/developers/dumps