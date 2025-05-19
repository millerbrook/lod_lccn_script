# Makefile for PRINT Project LCCN Workflow
#
# USAGE:
#   make
#     - Runs the workflow with ALL rows from the Excel file (default).
#
#   make FILTER_RED_FLAG=--filter-red
#     - Runs the workflow filtering ONLY rows with red "Researcher/Date" cells.
#
# The FILTER_RED_FLAG variable is passed to 01_get_target_persons.py.
# By default, it is empty (all rows). Set it to --filter-red to filter by red.

# Main output: Excel workbook bundling all results for users to download
all: data/bundle_persons_titles_lccn_missing.xlsx

# Step 1: Extract target persons from the master Excel file
# Input:  data/standard_directory_persons.xlsx
# Output: data/target_persons.csv (temporary)
FILTER_RED_FLAG ?=
data/target_persons.csv: data/standard_directory_persons.xlsx
	python 01_get_target_persons.py $(FILTER_RED_FLAG)

# Step 2: Generate skeletal persons DataFrame with titles and sources
# Input:  data/target_persons.csv
# Output: data/df_persons_skeletal.csv (temporary)
data/df_persons_skeletal.csv: data/target_persons.csv
	python 02_get_titles.py

# Step 3: Extract unique source titles from skeletal DataFrame
# Input:  data/df_persons_skeletal.csv
# Output: data/unique_sources.txt (temporary)
data/unique_sources.txt: data/df_persons_skeletal.csv
	python 03_read_titles_from_df_persons_skeletal.py

# Step 4: Look up LCCNs for each unique source title
# Input:  data/unique_sources.txt
# Output: data/lccns.csv (temporary), data/titles_lccn.csv (persistent), data/missing_titles.csv (persistent)
data/lccns.csv data/titles_lccn.csv data/missing_titles.csv: data/unique_sources.txt
	python 04_get_lccns.py

# Step 5: Add LCCNs to the skeletal persons DataFrame
# Input:  data/df_persons_skeletal.csv, data/titles_lccn.csv
# Output: data/df_persons_skeletal_with_lccn.csv (temporary)
data/df_persons_skeletal_with_lccn.csv: data/df_persons_skeletal.csv data/titles_lccn.csv
	python 05_add_lccns_to_df_persons.py

# Step 6: Bundle all results into a single Excel workbook for users
# Input:  data/df_persons_skeletal.csv, data/titles_lccn.csv, data/missing_titles.csv
# Output: data/bundle_persons_titles_lccn_missing.xlsx (final output)
data/bundle_persons_titles_lccn_missing.xlsx: data/df_persons_skeletal.csv data/titles_lccn.csv data/missing_titles.csv
	python 06_bundle_df_persons_titles_lccn_missing_titles.py

# Clean up all intermediate/temporary files (keeps only the main output and persistent files)
clean:
	rm -f data/target_persons.csv data/df_persons_skeletal.csv data/unique_sources.txt data/lccns.csv data/df_persons_skeletal_with_lccn.csv