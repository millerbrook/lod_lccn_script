import pandas as pd
import requests
import time
import random
from thefuzz import fuzz  # Import thefuzz for fuzzy matching

def robust_request(url, params=None, max_retries=5, base_delay=2, verbose=True):
    """Request with exponential backoff and random jitter for rate limiting."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response
            elif response.status_code == 429:
                wait = base_delay * (2 ** attempt) + random.uniform(0, 1)
                if verbose:
                    print(f"Rate limited. Sleeping for {wait:.2f} seconds...")
                time.sleep(wait)
            else:
                if verbose:
                    print(f"Error: {response.status_code} for URL: {url}")
                return None
        except requests.RequestException as e:
            if verbose:
                print(f"Request failed: {e}")
            time.sleep(base_delay * (2 ** attempt) + random.uniform(0, 1))
    if verbose:
        print("Failed after retries.")
    return None

def get_lccn_for_title(title, max_retries=5, delay=1.5, threshold=90, verbose=True):
    """
    Searches for LCCNs for a given title using the Library of Congress search API.
    """
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
    Confirms LCCNs by comparing titles using fuzzy matching.
    """
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
    # Create DataFrame and save to CSV instead of Excel
    confirmed_df = pd.DataFrame(confirmed_titles_lccn)
    confirmed_df.to_csv('titles_lccn.csv', index=False)
    return df, confirmed_df

def get_title_from_lccn(lccn, delay=1.5, max_retries=5, verbose=True):
    """
    Retrieves the title of a book using its LCCN from the Library of Congress JSON API.
    """
    url = f"https://www.loc.gov/item/{lccn}/?fo=json"
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
    data = {
         'source': ['Sample', 'Sample', 'Sample', 'Sample', 'Sample', 'Sample'],
         'title': [
             'The Adventures of Captain John Smith',
             'Pride and Prejudice', 
            'Beloved',
            'A Farewell to Arms',
            'Sense and Sensibility',
            'A Fine Balance'
         ],
         'DoB Source': ['', '', '', '', "", ''],
         'DoD Source': ['', '', '', '', "", ''],
         'DoD (P570) Source': ['', '', '', '', '', ''],
         'P26+P2562 Source': ['', '', '', '', '', '']
     }
    df = pd.DataFrame(data)
    df['LCCN'] = df['title'].apply(get_lccn_for_title)
    print("\nInitial DataFrame with LCCNs:")
    print(df)

    # Confirm LCCNs and build spreadsheet
    df, confirmed_df = confirm_lccn_matches(df, 'LCCN', 'title')
    print("\nDataFrame after confirmation:")
    print(df)
    print("\nConfirmed Titles and LCCNs:")
    print(confirmed_df)