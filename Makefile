# Makefile for PRINT Project LCCN Workflow

# Set default Python interpreter (override with `make PYTHON=python` on Windows)
PYTHON ?= python3

# USAGE:
#   make
#     - Runs the workflow with ALL rows from the Excel file (default).
#
#   make FILTER_RED_FLAG=--filter-red
#     - Runs the workflow filtering ONLY rows with red "Researcher/Date" cells.
#
#   make bundle
#     - Runs the full workflow including the final bundling step
#
#   make clean
#     - Removes temporary files but preserves titles_lccn.csv and the final bundle

# Main workflow: run all steps in order
all: data/titles_lccn.csv

# Complete workflow including bundling
bundle: data/bundle_persons_titles_lccn_missing.xlsx

# Step 1: Extract target persons from the master Excel file
# Input:  data/standard_directory_persons.xlsx
# Output: data/target_persons.csv (temporary)
FILTER_RED_FLAG ?=
data/target_persons.csv: data/standard_directory_persons.xlsx
	$(PYTHON) 01_get_target_persons.py $(FILTER_RED_FLAG)

# Step 2: Generate skeletal persons DataFrame with titles and sources
# Input:  data/target_persons.csv
# Output: data/df_persons_skeletal.csv (temporary)
data/df_persons_skeletal.csv: data/target_persons.csv
	$(PYTHON) 02_make_source_columns.py

# Step 3: Extract unique source titles from skeletal DataFrame
# Input:  data/df_persons_skeletal.csv
# Output: data/unique_sources.txt (temporary)
data/unique_sources.txt: data/df_persons_skeletal.csv
	$(PYTHON) 03_read_titles_from_df_persons_skeletal.py

# Step 4: Update titles_lccn.csv using unique_sources.txt
# Input:  data/unique_sources.txt
# Output: data/titles_lccn.csv (persistent)
# This step runs the new LCCN lookup workflow, which queries LOC and Open Library for each unique source title,
# and appends results to data/titles_lccn.csv (skipping titles already present).
data/titles_lccn.csv: data/unique_sources.txt
	$(PYTHON) 04_lccn_from_openlib_then_loc.py

# Step 5: Add LCCNs to the skeletal persons DataFrame
# Input:  data/df_persons_skeletal.csv, data/titles_lccn.csv
# Output: data/df_persons_skeletal_with_lccn.csv (temporary)
data/df_persons_skeletal_with_lccn.csv: data/df_persons_skeletal.csv data/titles_lccn.csv
	$(PYTHON) 05_add_lccns_to_df_persons.py

# Step 6: Bundle all results into a single Excel workbook
# Input:  data/df_persons_skeletal_with_lccn.csv, data/titles_lccn.csv, data/missing_titles.csv
# Output: data/bundle_persons_titles_lccn_missing.xlsx (final output)
data/bundle_persons_titles_lccn_missing.xlsx: data/df_persons_skeletal_with_lccn.csv data/titles_lccn.csv
	$(PYTHON) 06_bundle_df_persons_titles_lccn_missing_titles.py

# Archive important output files with date stamps
.PHONY: archive
archive: data/titles_lccn.csv data/bundle_persons_titles_lccn_missing.xlsx
	@echo "Creating date-stamped archives..."
	@mkdir -p data/archives
	@DATE=$$(date +%Y-%m-%d); \
	cp data/titles_lccn.csv "data/archives/titles_lccn_$$DATE.csv"; \
	cp data/bundle_persons_titles_lccn_missing.xlsx "data/archives/bundle_persons_titles_lccn_missing_$$DATE.xlsx"; \
	echo "Archives created with date stamp $$DATE"

# Clean up temporary files
# Preserves: titles_lccn.csv and bundle_persons_titles_lccn_missing.xlsx
.PHONY: clean
clean:
	rm -f data/target_persons.csv
	rm -f data/df_persons_skeletal.csv
	rm -f data/unique_sources.txt
	rm -f data/df_persons_skeletal_with_lccn.csv
	# Note: We keep titles_lccn.csv to avoid redoing searches
	@echo "Cleaned temporary files while preserving persistent data files"

# Complete workflow with targets
# make              - Run through Step 4 (titles_lccn.csv)
# make bundle       - Run full workflow including bundling
# make archive      - Create date-stamped archives of output files
# make clean        - Remove temporary files
.PHONY: bundle
bundle: data/bundle_persons_titles_lccn_missing.xlsx