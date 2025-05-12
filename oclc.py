import pandas as pd
import requests
from difflib import SequenceMatcher

# Step 1: Create a simple DataFrame
data = {
    'source': ['Sample', 'Sample'],
    'title': ['Self-Consciousness in Modern British Fiction', 'Fictions of State: Culture and Credit in Britain, 1694-1994']
}
df = pd.DataFrame(data)

def similar(a, b):
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()

def get_oclc_for_title(title, api_key="YOUR_OCLC_API_KEY", verbose=False, threshold=0.90):
    url = "https://www.worldcat.org/webservices/catalog/search/worldcat/opensearch"
    params = {
        'q': title,
        'wskey': api_key,
        'format': 'json'
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        if verbose:
            print(f"Error: Received status code {response.status_code} for '{title}'")
        return []

    try:
        results = response.json().get('entries', [])
    except Exception:
        if verbose:
            print(f"Could not parse JSON for '{title}'")
        return []

    if not results:
        if verbose:
            print(f"No results for '{title}'")
        return []

    oclcs = []
    for item in results:
        item_title = item.get('title', '').strip()
        oclc_number = item.get('oclcnum') or item.get('oclcNumber') or item.get('oclc')
        sim_score = similar(title, item_title)
        if verbose:
            print(f"API Result - Title: {item_title} | OCLC: {oclc_number} | Similarity: {sim_score:.2f}")
        if sim_score >= threshold and oclc_number:
            if isinstance(oclc_number, list):
                oclcs.extend(oclc_number)
            else:
                oclcs.append(oclc_number)
            if len(oclcs) >= 5:
                break
    return oclcs[:5]

# Step 3: Apply function to DataFrame and create 'OCLC' column
df['OCLC'] = df['title'].apply(get_oclc_for_title)

print("\nFinal DataFrame:")
print(df)