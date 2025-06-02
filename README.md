# LCCN Script Project

Before running make, create and activate your virtual environment (e.g., python3 -m venv venv && source venv/bin/activate). All dependencies should be installed in the active environment.

## Downloading the Open Library Editions Data Dump

The script `test_open_library_dump.py` expects the Open Library editions data dump in gzipped format at ol_dump_editions_latest.txt.gz.

### Downloading with aria2 (Recommended for Large Files)

1. [Download aria2](https://github.com/aria2/aria2/releases) and extract it to a convenient folder.
2. Open a terminal or command prompt in your project directory.
3. Make sure the data folder exists:
```sh
mkdir data
```
4. Run the following command to download the file using multiple connections for faster speed:
```sh
./aria2c.exe -x 8 -s 8 https://openlibrary.org/data/ol_dump_editions_latest.txt.gz -d data
```
*(On Windows, use `aria2c.exe` instead of `./aria2c.exe` if not using a bash terminal.)*

You can find more information and other dumps at:  
https://openlibrary.org/developers/dumps

## Using the Makefile

This project includes a Makefile to simplify common tasks. Here are the available commands:

### Setup and Installation

```sh
make setup
```
Installs all dependencies from requirements.txt into your active virtual environment.

### Running Tests

```sh
make test
```
Runs all unit tests for the project.

### Processing the Data

```sh
make process
```
Processes the Open Library data dump to extract LCCN information.

### Cleaning Generated Files

```sh
make clean
```
Removes all generated files and temporary artifacts.

### Full Pipeline

```sh
make all
```
Runs the complete pipeline: setup, process data, and run tests.