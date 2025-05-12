import time
import random
import requests

def robust_request(url, max_retries=5, base_delay=2, verbose=True):
    """
    Makes a robust HTTP GET request with retries and exponential backoff.
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response
            elif response.status_code == 429:  # Too many requests
                wait = base_delay * (2 ** attempt) + random.uniform(0, 1)
                if verbose:
                    print(f"Rate limited. Retrying in {wait:.2f} seconds...")
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
        print("Max retries reached. Request failed.")
    return None

def get_title_from_lccn_json(lccn, delay=1.5, max_retries=5, verbose=True):
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

if __name__ == "__main__":
    # Example LCCN for testing
    test_lccn = "2002022641"  # Replace with a valid LCCN for testing
    print(f"Testing get_title_from_lccn_json with LCCN: {test_lccn}")
    title = get_title_from_lccn_json(test_lccn, verbose=True)
    if title:
        print(f"Test passed. Retrieved title: {title}")
    else:
        print("Test failed. No title retrieved.")