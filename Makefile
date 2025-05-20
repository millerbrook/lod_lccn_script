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
#   make BATCH_SIZE=50 BATCH_INDEX=0
#     - Runs the LCCN lookup for batch 0 of size 50.
#
#   make all_batches BATCH_SIZE=50
#     - Runs the LCCN lookup for ALL batches sequentially (each batch as a separate make call).
#
# The FILTER_RED_FLAG variable is passed to 01_get_target_persons.py.
# The BATCH_SIZE and BATCH_INDEX variables are passed to 04_get_lccns.py.
# The all_batches target will run all batches in order using the specified BATCH_SIZE.

# Main output: Excel workbook bundling all results for users to download
all: data/bundle_persons_titles_lccn_missing.xlsx

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
	$(PYTHON) 02_get_titles.py

# Step 3: Extract unique source titles from skeletal DataFrame
# Input:  data/df_persons_skeletal.csv
# Output: data/unique_sources.txt (temporary)
data/unique_sources.txt: data/df_persons_skeletal.csv
	$(PYTHON) 03_read_titles_from_df_persons_skeletal.py

# Step 4: Add LCCNs to the skeletal persons DataFrame
# Input:  data/df_persons_skeletal.csv, data/titles_lccn.csv
# Output: data/df_persons_skeletal_with_lccn.csv (temporary)
data/df_persons_skeletal_with_lccn.csv: data/df_persons_skeletal.csv data/titles_lccn.csv
	$(PYTHON) 05_add_lccns_to_df_persons.py

# Step 5: Bundle all results into a single Excel workbook for users
# Input:  data/df_persons_skeletal.csv, data/titles_lccn.csv, data/missing_titles.csv
# Output: data/bundle_persons_titles_lccn_missing.xlsx (final output)
data/bundle_persons_titles_lccn_missing.xlsx: data/df_persons_skeletal.csv data/titles_lccn.csv data/missing_titles.csv
	$(PYTHON) 06_bundle_df_persons_titles_lccn_missing_titles.py

# Clean up all intermediate/temporary files (keeps only the main output and persistent files)
clean:
	rm -f data/target_persons.csv data/df_persons_skeletal.csv data/unique_sources.txt data/lccns.csv data/df_persons_skeletal_with_lccn.csv

# Run all batches using Makefile variables
# Usage: make all_batches BATCH_SIZE=50
.PHONY: batch all_batches

batch:
	$(PYTHON) 04_get_lccns.py $(if $(BATCH_SIZE),--batch-size $(BATCH_SIZE)) $(if $(BATCH_INDEX),--batch-index $(BATCH_INDEX))

all_batches: data/unique_sources.txt
	@total=$$(wc -l < data/unique_sources.txt); \
	batch_size=$(BATCH_SIZE); \
	num_batches=$$(( (total + batch_size - 1) / batch_size )); \
	for i in $$(seq 0 $$((num_batches - 1))); do \
		$(MAKE) batch BATCH_SIZE=$(BATCH_SIZE) BATCH_INDEX=$$i || exit $$?; \
	done