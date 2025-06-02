import pandas as pd
import numpy as np
import re
from datetime import datetime

def process_date_columns(row):
    handlebars_columns = {
        'Birth Date': 'DoB Source URL',
        'Death Date': 'DoD Source URL',
        'Marriage Date': 'P26+P2562 Source URL'
    }
    brackets_columns = {
        'Birth Date': 'DoB Source',
        'Death Date': 'DoD (P570) Source',
        'Marriage Date': 'P26+P2562 Source'
    }
    for col, target_col in handlebars_columns.items():
        if pd.notna(row[col]) and isinstance(row[col], str):
            matches = re.findall(r'\{\{(.*?)\}\}', row[col])
            if matches:
                row[col] = re.sub(r'\{\{.*?\}\}', '', row[col]).strip()
                source_text = '; '.join(matches)
                if pd.notna(row[target_col]) and row[target_col].strip():
                    row[target_col] += '; ' + source_text
                else:
                    row[target_col] = source_text
    for col, target_col in brackets_columns.items():
        if pd.notna(row[col]) and isinstance(row[col], str):
            matches = re.findall(r'\[\[(.*?)\]\]', row[col])
            if matches:
                row[col] = re.sub(r'\[\[.*?\]\]', '', row[col]).strip()
                source_text = '; '.join(matches)
                if pd.notna(row[target_col]) and row[target_col].strip():
                    row[target_col] += '; ' + source_text
                else:
                    row[target_col] = source_text
    return row

def strip_whitespace_from_specific_columns(df):
    columns_to_clean = [
        'Birth Date', 'Death Date', 'Marriage Date',
        'DoB Source', 'DoD (P570) Source', 'P26+P2562 Source',
        'DoB Source URL', 'DoD Source URL', 'P26+P2562 Source URL'
    ]
    for col in columns_to_clean:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    return df

def fix_partial_date(date_str):
    if pd.isna(date_str) or date_str.strip() == '':
        return None
    date_str = date_str.strip()
    try:
        if date_str.endswith('-00-00'):
            year = int(date_str[:4])
            return datetime(year, 1, 1)
        elif date_str.endswith('-00'):
            year, month = map(int, date_str.split('-')[:2])
            return datetime(year, month, 1)
        else:
            return pd.to_datetime(date_str, errors='coerce')
    except Exception:
        return None

def process_place_columns(row):
    handlebars_columns = {
        'Place of Birth (P19)': 'PoB Source URL',
        'Place of Death': 'Place of Death Source URL',
        'Place of Residence': 'Place of Residence Source URL'
    }
    brackets_columns = {
        'Place of Birth (P19)': 'PoB Source',
        'Place of Death': 'Place of Death Source',
        'Place of Residence': 'Place of Residence Source'
    }
    for col, target_col in handlebars_columns.items():
        if pd.notna(row[col]) and isinstance(row[col], str):
            matches = re.findall(r'\{\{(.*?)\}\}', row[col])
            if matches:
                row[col] = re.sub(r'\{\{.*?\}\}', '', row[col]).strip()
                source_text = '; '.join(matches)
                if pd.notna(row[target_col]) and row[target_col].strip():
                    row[target_col] += '; ' + source_text
                else:
                    row[target_col] = source_text
    for col, target_col in brackets_columns.items():
        if pd.notna(row[col]) and isinstance(row[col], str):
            matches = re.findall(r'\[\[(.*?)\]\]', row[col])
            if matches:
                row[col] = re.sub(r'\[\[.*?\]\]', '', row[col]).strip()
                source_text = '; '.join(matches)
                if pd.notna(row[target_col]) and row[target_col].strip():
                    row[target_col] += '; ' + source_text
                else:
                    row[target_col] = source_text
    return row

def process_occupation_column(row):
    handlebars_column = 'Occupation Source URL'
    if pd.notna(row['Occupation']) and isinstance(row['Occupation'], str):
        matches = re.findall(r'\{\{(.*?)\}\}', row['Occupation'])
        if matches:
            row['Occupation'] = re.sub(r'\{\{.*?\}\}', '', row['Occupation']).strip()
            source_text = '; '.join(matches)
            if pd.notna(row[handlebars_column]) and row[handlebars_column].strip():
                row[handlebars_column] += '; ' + source_text
            else:
                row[handlebars_column] = source_text
    if pd.notna(row['Occupation']) and isinstance(row['Occupation'], str):
        matches = re.findall(r'\[\[(.*?)\]\]', row['Occupation'])
        if matches:
            row['Occupation'] = re.sub(r'\[\[.*?\]\]', '', row['Occupation']).strip()
            source_text = '; '.join(matches)
            if pd.notna(row['Occupation Source']) and row['Occupation Source'].strip():
                row['Occupation Source'] += '; ' + source_text
            else:
                row['Occupation Source'] = source_text
    return row

def process_persons_dataframe(df_2):
    # Remove sampling to include all rows
    df_persons = df_2.replace('', np.nan, regex=True)
    np.random.seed(1)

    # Drop unnecessary columns
    df_persons.drop(['Mention only?', 'Researcher/Date'], axis=1, inplace=True)

    # Data cleaning
    df_persons.dropna(how='all', inplace=True)
    df_persons = df_persons[df_persons['Authority Terms'].notna()]
    df_persons = df_persons[~df_persons['Authority Terms'].str.contains(r'\[|\]|\(|\)')]
    df_persons.rename(columns={"Authority Terms": "name"}, inplace=True)

    # Add empty columns for sources
    df_persons['DoB Source'] = ''
    df_persons['DoD (P570) Source'] = ''
    df_persons['P26+P2562 Source'] = ''
    df_persons['DoB Source URL'] = ''
    df_persons['DoD Source URL'] = ''
    df_persons['P26+P2562 Source URL'] = ''

    # Process date columns
    df_persons = df_persons.apply(process_date_columns, axis=1)
    df_persons = strip_whitespace_from_specific_columns(df_persons)

    # Handle partial dates
    date_columns = ['Birth Date', 'Death Date', 'Marriage Date']
    for col in date_columns:
        df_persons[col] = df_persons[col].astype(str).apply(
            lambda x: fix_partial_date(x) if pd.notna(fix_partial_date(x)) else x
        )

    # Place and occupation columns
    df_persons.rename(columns={
        'Birth Place': 'Place of Birth (P19)',
        'Death Place': 'Place of Death',
        'Place of Residence': 'Place of Residence'
    }, inplace=True)

    df_persons['PoB Source'] = ''
    df_persons['Place of Death Source'] = ''
    df_persons['Place of Residence Source'] = ''
    df_persons['PoB Source URL'] = ''
    df_persons['Place of Death Source URL'] = ''
    df_persons['Place of Residence Source URL'] = ''
    df_persons['Occupation Source URL'] = ''

    df_persons = df_persons.apply(process_place_columns, axis=1)
    df_persons = df_persons.apply(process_occupation_column, axis=1)

    columns_to_clean = [
        'Place of Birth (P19)', 'Place of Death', 'Place of Residence', 'Occupation',
        'PoB Source', 'Place of Death Source', 'Place of Residence Source', 'Occupation Source',
        'PoB Source URL', 'Place of Death Source URL', 'Place of Residence Source URL', 'Occupation Source URL'
    ]
    for col in columns_to_clean:
        if col in df_persons.columns:
            df_persons[col] = df_persons[col].astype(str).str.strip()

    # Export skeletal DataFrame to the data folder
    output_path = 'data/df_persons_skeletal.csv'
    df_persons_skeletal = df_persons[['name', 'AltLastName', 'AltMiddleName', 'AltFirstName', 'Maiden Name', 'Title', 'Birth Date', 'DoB Source', 'DoB Source URL', 'Death Date', 'DoD (P570) Source', 'DoD Source URL', 'Marriage Date', 'P26+P2562 Source', 'P26+P2562 Source URL', 'Source for Dates', 'Place of Birth (P19)', 'PoB Source', 'PoB Source URL', 'Place of Death', 'Place of Death Source', 'Place of Death Source URL', 'Place of Residence', 'Place of Residence Source', 'Place of Residence Source URL', 'Source for Places', 'Occupation', 'Occupation Source', 'Occupation Source URL', 'Gender', 'LOD - WikiData']]
    df_persons_skeletal.to_csv(output_path, index=False, encoding='utf-8-sig')

if __name__ == "__main__":
    # Read target_persons.csv as df_2
    df_2 = pd.read_csv('data/target_persons.csv', encoding='utf-8-sig')
    process_persons_dataframe(df_2)