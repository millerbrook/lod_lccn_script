all: data/lccns.csv

data/target_persons.csv:
	python 01_get_target_persons.py

data/df_persons_skeletal.csv: data/target_persons.csv
	python 02_get_titles.py

data/unique_sources.txt: data/df_persons_skeletal.csv
	python 03_read_titles_from_df_persons_skeletal.py

data/lccns.csv: data/unique_sources.txt
	python 04_get_lccns.py

clean:
	rm -f data/target_persons.csv data/df_persons_skeletal.csv data/unique_sources.txt data/lccns.csv