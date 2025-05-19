import pandas as pd

# Load data
df = pd.read_csv('data/df_persons_skeletal.csv', encoding='utf-8-sig')
titles_lccn = pd.read_csv('data/titles_lccn.csv', encoding='utf-8-sig')

# Build a lookup dictionary for fast access
title_to_lccn = dict(zip(titles_lccn['Title'].astype(str).str.strip(), titles_lccn['LCCN']))

# Identify all columns that may contain titles (those with 'Source' in the name, but not 'URL')
title_columns = [col for col in df.columns if 'source' in col.lower() and 'url' not in col.lower()]

for col in title_columns:
    lccn_col = f"{col} LCCN"
    # Map each title in the column to its LCCN, or empty string if not found
    df[lccn_col] = df[col].astype(str).str.strip().map(title_to_lccn).fillna('')

# Save the updated DataFrame
df.to_csv('data/df_persons_skeletal_with_lccn.csv', index=False, encoding='utf-8-sig')
print("LCCN columns added and saved to data/df_persons_skeletal_with_lccn.csv")