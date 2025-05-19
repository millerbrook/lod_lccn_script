import pandas as pd
import requests
import time
import random
import re
from thefuzz import fuzz
from threading import Lock
import os
import argparse
import math

# Shared variables for rate limiting
request_count = 0
start_time = time.time()
lock = Lock()

def rate_limit(max_requests=9, time_window=60):
    """
    Ensures that no more than `max_requests` are made within `time_window` seconds.
    """
    global request_count, start_time
    with lock:
        current_time = time.time()
        elapsed_time = current_time - start_time

        if elapsed_time > time_window:
            request_count = 0
            start_time = current_time

        if request_count >= max_requests:
            wait_time = time_window - elapsed_time
            if wait_time > 0:
                print(f"Rate limit reached. Waiting for {wait_time:.2f} seconds...")
                time.sleep(wait_time)
                request_count = 0
                start_time = time.time()

        request_count += 1

def robust_request(url, params=None, max_retries=5, base_delay=6, verbose=True):
    """
    Makes a robust request with exponential backoff and rate limiting.
    """
    for attempt in range(max_retries):
        rate_limit()
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response
            elif response.status_code == 429:
                if attempt == max_retries - 1:
                    if verbose:
                        print("Rate limited by server. Waiting for 1 hour and 1 minute (3660 seconds) before retrying...")
                    time.sleep(3660)
                else:
                    wait = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    if verbose:
                        print(f"Rate limited by server. Retrying in {wait:.2f} seconds...")
                    time.sleep(wait)
            else:
                if verbose:
                    print(f"HTTP error {response.status_code} for URL: {url}")
                return None
        except requests.RequestException as e:
            if verbose:
                print(f"Request failed: {e}")
            time.sleep(base_delay * (2 ** attempt) + random.uniform(0, 1))
    if verbose:
        print("Failed after retries.")
    return None

def write_missing_titles(missing_titles, missing_titles_path='data/missing_titles.csv'):
    """
    Writes missing titles to missing_titles.csv, appending if the file exists.
    """
    missing_df = pd.DataFrame(missing_titles, columns=['Title', 'Reason'])
    try:
        existing = pd.read_csv(missing_titles_path)
        missing_df = pd.concat([existing, missing_df], ignore_index=True)
        missing_df = missing_df.drop_duplicates(subset=['Title', 'Reason'])
    except FileNotFoundError:
        pass
    missing_df.to_csv(missing_titles_path, index=False)

def screen_and_clean_title(title):
    """
    Screens a title for URLs and page numbers.
    Returns:
        cleaned_title: cleaned title string or None if not usable
        bad_reason: reason string if title is bad, else None
    """
    if not isinstance(title, str):
        return None, "not_a_string"
    title_strip = title.strip()
    if re.search(r'https?://|www\.', title_strip, re.IGNORECASE):
        return None, "url"
    page_pattern = r'(.*?)(?:\s*\bp\.\s*\d+(-\d+)?\b.*)$'
    match = re.match(page_pattern, title_strip, re.IGNORECASE)
    if match:
        cleaned = match.group(1).strip()
        if cleaned:
            return cleaned, None
        else:
            return None, "page_number"
    return title_strip, None

def write_bad_titles(bad_titles, bad_titles_path='data/bad_titles.csv'):
    """
    Writes bad titles to bad_titles.csv, appending if the file exists.
    """
    bad_df = pd.DataFrame(bad_titles, columns=['Title', 'Reason'])
    try:
        existing = pd.read_csv(bad_titles_path)
        bad_df = pd.concat([existing, bad_df], ignore_index=True)
        bad_df = bad_df.drop_duplicates(subset=['Title', 'Reason'])
    except FileNotFoundError:
        pass
    bad_df.to_csv(bad_titles_path, index=False)

def get_lccn_for_title(title, max_retries=5, delay=1.5, threshold=90, verbose=True):
    """
    Searches for LCCNs for a given title using the Library of Congress search API or reuses LCCNs from titles_lccn.csv.
    Screens for URLs and page numbers.
    """
    missing_titles = []
    cleaned_title, bad_reason = screen_and_clean_title(title)
    if bad_reason:
        missing_titles.append((safe_str(title), safe_str(bad_reason)))
        write_missing_titles(missing_titles)
        if verbose:
            print(f"Skipped bad title: {title} (Reason: {bad_reason})")
        return []
    title = cleaned_title

    try:
        titles_lccn_df = pd.read_csv('data/titles_lccn.csv')
        matching_row = titles_lccn_df[titles_lccn_df['Title'].str.strip().str.lower() == title.strip().lower()]
        if not matching_row.empty:
            lccn = matching_row.iloc[0]['LCCN']
            if verbose:
                print(f"Reused LCCN from titles_lccn.csv for '{title}': {lccn}")
            return [lccn] if pd.notna(lccn) else []
    except FileNotFoundError:
        if verbose:
            print("titles_lccn.csv not found. Proceeding with API request.")

    url = "https://www.loc.gov/search/"
    params = {
        'all': 'true',
        'q': title,
        'fo': 'json',
        'fa': 'original-format:book',
    }
    response = robust_request(url, params=params, max_retries=max_retries, base_delay=delay, verbose=verbose)
    if response is None:
        missing_titles.append((safe_str(title), "lccn not found"))
        write_missing_titles(missing_titles)
        return []

    results = response.json().get('results', [])
    if not results:
        if verbose:
            print(f"No results for '{title}'")
        time.sleep(delay + random.uniform(0, 1))
        missing_titles.append((safe_str(title), "lccn not found"))
        write_missing_titles(missing_titles)
        return []

    lccns = []
    matches = []
    for item in results:
        item_title = item.get('title', '').strip()
        number_lccn = item.get('number_lccn')
        sim_sort = fuzz.token_sort_ratio(title, item_title)
        if sim_sort >= threshold:
            if verbose:
                print(f"Matched with token_sort_ratio: {sim_sort} | Title: {item_title}")
            matches.append((item_title, number_lccn))
            if isinstance(number_lccn, list):
                lccns.extend(number_lccn)
            else:
                lccns.append(number_lccn)
            continue

        sim_set = fuzz.token_set_ratio(title, item_title)
        if sim_set >= threshold:
            if verbose:
                print(f"Matched with token_set_ratio: {sim_set} | Title: {item_title}")
            matches.append((item_title, number_lccn))
            if isinstance(number_lccn, list):
                lccns.extend(number_lccn)
            else:
                lccns.append(number_lccn)

    if not lccns:
        missing_titles.append((safe_str(title), "lccn not found"))
        write_missing_titles(missing_titles)

    if matches and verbose:
        print(f"\nMatches for '{title}':")
        for t, l in matches:
            print(f"  Title: {t}\n  LCCN: {l}")
    time.sleep(delay + random.uniform(0, 1))
    return lccns[:5]

def confirm_lccn_matches(df, lccn_col, title_col, delay=1.5, sim_threshold=95, max_retries=5, verbose=True):
    """
    Confirms LCCNs by comparing titles using fuzzy matching and appends results to titles_lccn.csv.
    Ensures no duplicate lines in titles_lccn.csv.
    """
    rate_limit()
    confirmed_titles_lccn = []
    for idx, row in df.iterrows():
        orig_title = row[title_col]
        lccn_list = row[lccn_col]
        if not lccn_list or not isinstance(lccn_list, list):
            continue
        found = False
        for lccn in lccn_list:
            title_from_lccn = get_title_from_lccn(lccn, delay=delay, max_retries=max_retries, verbose=verbose)
            if title_from_lccn:
                sim_sort = fuzz.token_sort_ratio(orig_title, title_from_lccn)
                if sim_sort >= sim_threshold:
                    if verbose:
                        print(f"Confirmed with token_sort_ratio: {sim_sort} | Title: {title_from_lccn}")
                    df.at[idx, lccn_col] = [lccn]
                    confirmed_titles_lccn.append({'Title': title_from_lccn, 'LCCN': lccn})
                    found = True
                    break

                sim_set = fuzz.token_set_ratio(orig_title, title_from_lccn)
                if sim_set >= sim_threshold:
                    if verbose:
                        print(f"Confirmed with token_set_ratio: {sim_set} | Title: {title_from_lccn}")
                    df.at[idx, lccn_col] = [lccn]
                    confirmed_titles_lccn.append({'Title': title_from_lccn, 'LCCN': lccn})
                    found = True
                    break
        if not found:
            df.at[idx, lccn_col] = []

    confirmed_df = pd.DataFrame(confirmed_titles_lccn)
    if not confirmed_df.empty:
        try:
            existing_df = pd.read_csv('./data/titles_lccn.csv')
            combined_df = pd.concat([existing_df, confirmed_df], ignore_index=True)
            combined_df = combined_df.drop_duplicates(subset=['Title', 'LCCN'], keep='first')
        except FileNotFoundError:
            combined_df = confirmed_df
        combined_df.to_csv('data/titles_lccn.csv', index=False)
    return df, confirmed_df

def get_title_from_lccn(lccn, delay=1.5, max_retries=5, verbose=True):
    """
    Retrieves the title of a book using its LCCN from the Library of Congress JSON API.
    """
    url = f"https://www.loc.gov/item/{lccn}/?fo=json"
    rate_limit()  # Apply rate limiting before making the request
    response = robust_request(url, max_retries=max_retries, base_delay=delay, verbose=verbose)
    if response and response.status_code == 200:
        try:
            data = response.json()
            title = data.get('item', {}).get('title', None)
            if title:
                if verbose:
                    print(f"Retrieved title for LCCN {lccn}: {title}")
                return title
            else:
                if verbose:
                    print(f"No title found for LCCN {lccn}")
        except ValueError as e:
            if verbose:
                print(f"Error parsing JSON for LCCN {lccn}: {e}")
    else:
        if verbose:
            print(f"Failed to retrieve JSON for LCCN {lccn}")
    time.sleep(delay + random.uniform(0, 1))
    return None

def safe_str(val):
    """
    Ensures that the value is always a string.
    If the value is a list, joins its elements with '; '.
    This is important for writing to CSVs and for DataFrame operations like drop_duplicates,
    which require hashable (string) types and will error on lists.

    In this file, safe_str is used to guarantee that 'title' and 'reason' fields written to
    missing_titles.csv are always strings, even if the original value is a list. This prevents
    'TypeError: unhashable type: 'list'' when pandas tries to drop duplicates or process these columns.
    """
    if isinstance(val, list):
        return "; ".join(map(str, val))
    return str(val)

def process_batch(titles, verbose=True):
    df = pd.DataFrame({'title': titles})
    df['LCCN'] = df['title'].apply(get_lccn_for_title)
    df, confirmed_df = confirm_lccn_matches(df, 'LCCN', 'title')
    df.to_csv('data/lccns.csv', index=False, encoding='utf-8-sig')
    titles_lccn_path = 'data/titles_lccn.csv'

    # Convert LCCN lists to strings for deduplication
    df_out = df[['title', 'LCCN']].rename(columns={'title': 'Title'}).copy()
    df_out['LCCN'] = df_out['LCCN'].apply(safe_str)

    if os.path.exists(titles_lccn_path):
        existing = pd.read_csv(titles_lccn_path)
        # Ensure existing LCCN column is string
        if 'LCCN' in existing.columns:
            existing['LCCN'] = existing['LCCN'].apply(safe_str)
        combined = pd.concat([existing, df_out], ignore_index=True)
        combined = combined.drop_duplicates(subset=['Title', 'LCCN'])
    else:
        combined = df_out
    combined.to_csv(titles_lccn_path, index=False, encoding='utf-8-sig')

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch-size', type=int, default=None, help='Number of titles to process in this batch')
    parser.add_argument('--batch-index', type=int, default=0, help='Batch index (0-based)')
    parser.add_argument('--all-batches', action='store_true', help='Process all batches sequentially')
    args = parser.parse_args()

    with open('data/unique_sources.txt', 'r', encoding='utf-8') as f:
        titles = [line.strip() for line in f if line.strip()]

    if args.batch_size and args.all_batches:
        num_batches = math.ceil(len(titles) / args.batch_size)
        for batch_idx in range(num_batches):
            start = batch_idx * args.batch_size
            end = start + args.batch_size
            batch_titles = titles[start:end]
            print(f"Processing batch {batch_idx} (titles {start} to {end-1})")
            process_batch(batch_titles)
            print(f"Batch {batch_idx} complete. Processed {len(batch_titles)} titles.")
    else:
        if args.batch_size:
            start = args.batch_index * args.batch_size
            end = start + args.batch_size
            titles = titles[start:end]
            print(f"Processing batch {args.batch_index} (titles {start} to {end-1})")
        process_batch(titles)
        print(f"Batch {args.batch_index if args.batch_size else 0} complete. Processed {len(titles)} titles.")