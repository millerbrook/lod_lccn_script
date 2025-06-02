import pandas as pd
import ast

# Load data
df = pd.read_csv('data/df_persons_skeletal.csv', encoding='utf-8-sig')
titles_lccn = pd.read_csv('data/titles_lccn.csv', encoding='utf-8-sig')

# Build lookup dictionaries for fast access
title_to_lccn = dict(zip(titles_lccn['Title'].astype(str).str.strip(), titles_lccn['LCCN']))
title_to_alt_lccn = dict(zip(titles_lccn['Title'].astype(str).str.strip(), titles_lccn['Alt_LCCN']))
title_to_oclc = dict(zip(titles_lccn['Title'].astype(str).str.strip(), titles_lccn['OCLC']))
title_to_alt_oclc = dict(zip(titles_lccn['Title'].astype(str).str.strip(), titles_lccn['Alt_OCLC']))

# Function to safely parse string representations of lists
def safe_parse_list(list_str):
    if pd.isna(list_str) or list_str == '':
        return ''
    try:
        # Parse the string representation of a list
        parsed = ast.literal_eval(list_str)
        if isinstance(parsed, list):
            return parsed
        return ''
    except (ValueError, SyntaxError):
        return ''

# Identify all columns that may contain titles (those with 'Source' in the name, but not 'URL')
title_columns = [col for col in df.columns if 'source' in col.lower() and 'url' not in col.lower()]

for col in title_columns:
    # Create column names
    lccn_col = f"{col} LCCN"
    alt_lccn_col = f"{col} Alt_LCCN"
    oclc_col = f"{col} OCLC"
    alt_oclc_col = f"{col} Alt_OCLC"
    
    # Map titles to their identifiers
    df[lccn_col] = df[col].astype(str).str.strip().map(title_to_lccn).fillna('')
    
    # Handle list columns with special parsing
    df[alt_lccn_col] = df[col].astype(str).str.strip().map(
        lambda x: title_to_alt_lccn.get(x, '') if x in title_to_alt_lccn else ''
    )
    df[alt_lccn_col] = df[alt_lccn_col].apply(safe_parse_list)
    
    df[oclc_col] = df[col].astype(str).str.strip().map(title_to_oclc).fillna('')
    
    df[alt_oclc_col] = df[col].astype(str).str.strip().map(
        lambda x: title_to_alt_oclc.get(x, '') if x in title_to_alt_oclc else ''
    )
    df[alt_oclc_col] = df[alt_oclc_col].apply(safe_parse_list)

# Save the updated DataFrame
df.to_csv('data/df_persons_skeletal_with_lccn.csv', index=False, encoding='utf-8-sig')
print("LCCN, Alt_LCCN, OCLC, and Alt_OCLC columns added and saved to data/df_persons_skeletal_with_lccn.csv")