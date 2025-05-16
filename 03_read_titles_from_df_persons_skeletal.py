# This script reads a CSV file, extracts all values from columns containing 'source' in their names,
import pandas as pd

def get_unique_source_values(csv_path='data/df_persons_skeletal.csv'):
    """
    Reads the CSV and returns a list of unique, non-empty, stripped values
    from columns containing 'source' (case-insensitive) but not 'url'.
    """
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    source_cols = [
        col for col in df.columns
        if 'source' in col.lower() and 'url' not in col.lower()
    ]
    source_values = []
    for col in source_cols:
        source_values.extend(df[col].dropna().astype(str).tolist())
    source_values = sorted({val.strip() for val in source_values if val.strip()})
    return source_values

# Example usage:
if __name__ == "__main__":
    unique_sources = get_unique_source_values()
    with open('data/unique_sources.txt', 'w', encoding='utf-8') as f:
        for source in unique_sources:
            f.write(source + '\n')