all: data/lccns.csv

data/target_persons.csv: data/standard_directory_persons.xlsx
	python 01_get_target_persons.py # This script reads the Excel file and creates a CSV file with the target persons.
	# The CSV file is saved in the data directory.
	# It only includes records that are color-coded in red in the 'Researcher' column.

data/df_persons_skeletal.csv: data/target_persons.csv
	python 02_get_titles.py # This script reads the CSV file created in the previous step and creates a new CSV file with the titles of the target persons.
	# It adds source columns to the CSV file.

data/unique_sources.txt: data/df_persons_skeletal.csv
	python 03_read_titles_from_df_persons_skeletal.py

data/lccns.csv: data/unique_sources.txt
	python 04_get_lccns.py

clean:
	rm -f data/target_persons.csv data/df_persons_skeletal.csv data/unique_sources.txt data/lccns.csv