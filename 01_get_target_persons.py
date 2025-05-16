import openpyxl
import pandas as pd

def get_target_persons(filepath='data/Person and Places Directory 5 15 25.xlsx', sheetname='Person List'):
    # Load the workbook and sheet
    wb = openpyxl.load_workbook(filepath, data_only=True)
    ws = wb[sheetname]

    # Find the column index for 'Researcher/Date'
    header = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
    col_idx = header.index('Researcher/Date') + 1  # openpyxl is 1-based

    # Prepare to collect rows with red fill in 'Researcher/Date'
    rows_with_red = []
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        cell = row[col_idx - 1]
        fill = cell.fill
        # Check if the cell has a red fill (RGB 'FFFF0000' is standard red)
        if fill.fill_type is not None and fill.start_color.rgb in ('FFFF0000', 'FF0000'):
            rows_with_red.append([c.value for c in row])

    # Convert to DataFrame
    df_red = pd.DataFrame(rows_with_red, columns=header)

    # Exclude records with data length >= 5 in any column starting with 'LOD' or 'lod'
    lod_cols = [col for col in df_red.columns if str(col).lower().startswith('lod')]
    mask = df_red[lod_cols].applymap(lambda x: len(str(x)) if pd.notnull(x) else 0)
    exclude_mask = (mask >= 5).any(axis=1)
    df_red_filtered = df_red[~exclude_mask]

    # Write to CSV in the data folder
    df_red_filtered.to_csv('data/target_persons.csv', index=False, encoding='utf-8-sig')

if __name__ == "__main__":
    get_target_persons()
    print("target_persons.csv written to data folder.")