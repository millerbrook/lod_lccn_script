import pandas as pd
import requests
import time
import random
import re
from thefuzz import fuzz  # Import thefuzz for fuzzy matching
from threading import Lock
import os

# Shared variables for rate limiting
request_count = 0
start_time = time.time()
lock = Lock()

#fake comment
def rate_limit(max_requests=9, time_window=60):
    """
    Ensures that no more than `max_requests` are made within `time_window` seconds.
    """
    global request_count, start_time
    with lock:
        current_time = time.time()
        elapsed_time = current_time - start_time

        if elapsed_time > time_window:
            # Reset the counter and start time after the time window has passed
            request_count = 0
            start_time = current_time

        if request_count >= max_requests:
            # Wait until the time window resets
            wait_time = time_window - elapsed_time
            if wait_time > 0:
                print(f"Rate limit reached. Waiting for {wait_time:.2f} seconds...")
                time.sleep(wait_time)
                # Reset after waiting
                request_count = 0
                start_time = time.time()

        # Increment the request count
        request_count += 1

def robust_request(url, params=None, max_retries=5, base_delay=2, verbose=True):
    """
    Makes a robust request with exponential backoff and rate limiting.
    """
    for attempt in range(max_retries):
        rate_limit()  # Apply rate limiting before making the request
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response
            elif response.status_code == 429:  # Too many requests
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
    # 1. Check for URLs
    if re.search(r'https?://|www\.', title_strip, re.IGNORECASE):
        return None, "url"
    # 3. Check for page numbers like 'p.44', 'p. 44', 'p. 44-45'
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
    Screens for URLs, semicolons, and page numbers.
    """
    bad_titles = []
    cleaned_title, bad_reason = screen_and_clean_title(title)
    if bad_reason:
        bad_titles.append((title, bad_reason))
        write_bad_titles(bad_titles)
        if verbose:
            print(f"Skipped bad title: {title} (Reason: {bad_reason})")
        return []
    title = cleaned_title

    # Check if titles_lccn.csv exists and reuse LCCNs if the title matches
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

    # If no match in titles_lccn.csv, proceed with API request
    url = "https://www.loc.gov/search/"
    params = {
        'all': 'true',
        'q': title,
        'fo': 'json',
        'fa': 'original-format:book',
    }
    response = robust_request(url, params=params, max_retries=max_retries, base_delay=delay, verbose=verbose)
    if response is None:
        return []

    results = response.json().get('results', [])
    if not results:
        if verbose:
            print(f"No results for '{title}'")
        time.sleep(delay + random.uniform(0, 1))
        return []

    lccns = []
    matches = []
    for item in results:
        item_title = item.get('title', '').strip()
        number_lccn = item.get('number_lccn')
        
        # Use token_sort_ratio first
        sim_sort = fuzz.token_sort_ratio(title, item_title)
        if sim_sort >= threshold:
            if verbose:
                print(f"Matched with token_sort_ratio: {sim_sort} | Title: {item_title}")
            matches.append((item_title, number_lccn))
            if isinstance(number_lccn, list):
                lccns.extend(number_lccn)
            else:
                lccns.append(number_lccn)
            continue  # Skip token_set_ratio if token_sort_ratio already matches

        # Use token_set_ratio as a fallback
        sim_set = fuzz.token_set_ratio(title, item_title)
        if sim_set >= threshold:
            if verbose:
                print(f"Matched with token_set_ratio: {sim_set} | Title: {item_title}")
            matches.append((item_title, number_lccn))
            if isinstance(number_lccn, list):
                lccns.extend(number_lccn)
            else:
                lccns.append(number_lccn)

    if matches and verbose:
        print(f"\nMatches for '{title}':")
        for t, l in matches:
            print(f"  Title: {t}\n  LCCN: {l}")
    time.sleep(delay + random.uniform(0, 1))  # Sleep after each request to avoid being blocked
    return lccns[:5]

def confirm_lccn_matches(df, lccn_col, title_col, delay=1.5, sim_threshold=95, max_retries=5, verbose=True):
    """
    Confirms LCCNs by comparing titles using fuzzy matching and appends results to titles_lccn.csv.
    Ensures no duplicate lines in titles_lccn.csv.
    """
    rate_limit()  # Apply rate limiting before processing
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
                # Use token_sort_ratio first
                sim_sort = fuzz.token_sort_ratio(orig_title, title_from_lccn)
                if sim_sort >= sim_threshold:
                    if verbose:
                        print(f"Confirmed with token_sort_ratio: {sim_sort} | Title: {title_from_lccn}")
                    df.at[idx, lccn_col] = [lccn]
                    confirmed_titles_lccn.append({'Title': title_from_lccn, 'LCCN': lccn})
                    found = True
                    break  # Only keep the first confirmed match

                # Use token_set_ratio as a fallback
                sim_set = fuzz.token_set_ratio(orig_title, title_from_lccn)
                if sim_set >= sim_threshold:
                    if verbose:
                        print(f"Confirmed with token_set_ratio: {sim_set} | Title: {title_from_lccn}")
                    df.at[idx, lccn_col] = [lccn]
                    confirmed_titles_lccn.append({'Title': title_from_lccn, 'LCCN': lccn})
                    found = True
                    break
        if not found:
            # If no confirmed match, clear the cell
            df.at[idx, lccn_col] = []

    # Append to titles_lccn.csv without duplicates
    confirmed_df = pd.DataFrame(confirmed_titles_lccn)
    if not confirmed_df.empty:
        try:
            # Read existing titles_lccn.csv
            existing_df = pd.read_csv('./data/titles_lccn.csv')
            # Combine existing and new data
            combined_df = pd.concat([existing_df, confirmed_df], ignore_index=True)
            # Drop duplicates based on 'Title' and 'LCCN' columns
            combined_df = combined_df.drop_duplicates(subset=['Title', 'LCCN'], keep='first')
        except FileNotFoundError:
            # If the file doesn't exist, use only the new data
            combined_df = confirmed_df

        # Save the combined DataFrame back to data/titles_lccn.csv
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

# Example usage (uncomment to test as a script)
if __name__ == "__main__":
    # Read unique_sources.txt as a list of titles
    with open('data/unique_sources.txt', 'r', encoding='utf-8') as f:
        titles = [line.strip() for line in f if line.strip()]

    # Build DataFrame
    df = pd.DataFrame({'title': titles})

    # Get LCCNs for each title
    df['LCCN'] = df['title'].apply(get_lccn_for_title)

    # Confirm LCCNs and build spreadsheet
    df, confirmed_df = confirm_lccn_matches(df, 'LCCN', 'title')

    # Write the final DataFrame to lccns.csv in the data folder
    df.to_csv('data/lccns.csv', index=False, encoding='utf-8-sig')

    # Path to titles_lccn.csv
    titles_lccn_path = 'data/titles_lccn.csv'

    # Read existing titles_lccn.csv if it exists
    if os.path.exists(titles_lccn_path):
        existing = pd.read_csv(titles_lccn_path)
        combined = pd.concat([existing, df[['title', 'LCCN']].rename(columns={'title': 'Title'})], ignore_index=True)
        # Drop duplicates based on both Title and LCCN
        combined = combined.drop_duplicates(subset=['Title', 'LCCN'])
    else:
        combined = df[['title', 'LCCN']].rename(columns={'title': 'Title'})

    # Write back to titles_lccn.csv
    combined.to_csv(titles_lccn_path, index=False, encoding='utf-8-sig')

    print("\nDataFrame with LCCNs written to 'data/lccns.csv'")