import pandas as pd

# Read the CSV files
df_persons = pd.read_csv('data/df_persons_skeletal_with_lccn.csv', encoding='utf-8-sig')  # Updated to use file with LCCN
titles_lccn = pd.read_csv('data/titles_lccn.csv', encoding='utf-8-sig')
missing_titles = pd.read_csv('data/missing_titles.csv', encoding='utf-8-sig')

# Write to a single Excel workbook with separate sheets
with pd.ExcelWriter('data/bundle_persons_titles_lccn_missing.xlsx', engine='openpyxl') as writer:
    df_persons.to_excel(writer, sheet_name='Persons with LCCN', index=False)  # Updated sheet name to be more descriptive
    titles_lccn.to_excel(writer, sheet_name='Titles LCCN', index=False)
    missing_titles.to_excel(writer, sheet_name='Missing Titles', index=False)

print("Bundled workbook written to data/bundle_persons_titles_lccn_missing.xlsx")