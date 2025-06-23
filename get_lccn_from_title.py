import requests
import os
import json
from rapidfuzz import fuzz
import re
import urllib.parse
import xml.etree.ElementTree as ET  # Add this import for XML parsing

# Add the missing function
def parse_xml_response(response):
    """Parse XML response to extract LCCN and other identifiers."""
    try:
        # Parse the XML while preserving namespaces
        root = ET.fromstring(response.text)
        
        # Register namespaces needed for XPath
        namespaces = {
            'zs': 'http://www.loc.gov/zing/srw/',
            'mods': 'http://www.loc.gov/mods/v3'
        }
        
        # Find all records
        records = root.findall('.//zs:record', namespaces)
        print(f"Found {len(records)} records in response")
        
        all_titles = []
        all_lccns = []
        all_oclcs = []
        
        # Process each record
        for i, record in enumerate(records, 1):
            print(f"\n--- Record {i} ---")
            
            # Find title elements using proper namespace
            title_elements = record.findall('.//mods:titleInfo/mods:title', namespaces)
            if title_elements:
                for elem in title_elements:
                    title_text = elem.text
                    all_titles.append(title_text)
                    print(f"Title: {title_text}")
                    
                    # Check for subtitles
                    subtitle = record.find('.//mods:titleInfo/mods:subTitle', namespaces)
                    if subtitle is not None and subtitle.text:
                        print(f"Subtitle: {subtitle.text}")
            
            # Find LCCN identifiers using proper namespace
            lccn_elements = record.findall('.//mods:identifier[@type="lccn"]', namespaces)
            if lccn_elements:
                for elem in lccn_elements:
                    lccn_text = elem.text
                    all_lccns.append(lccn_text)
                    print(f"LCCN: {lccn_text}")
            
            # Find OCLC identifiers using proper namespace
            oclc_elements = record.findall('.//mods:identifier[@type="oclc"]', namespaces)
            if oclc_elements:
                for elem in oclc_elements:
                    oclc_text = elem.text
                    all_oclcs.append(oclc_text)
                    print(f"OCLC: {oclc_text}")
            
            # Also check for classification codes, which can be useful
            class_elements = record.findall('.//mods:classification[@authority="lcc"]', namespaces)
            if class_elements:
                for elem in class_elements:
                    print(f"LC Classification: {elem.text}")
        
        # Return the first LCCN if any were found, otherwise n/a
        return {
            "lccn": all_lccns[0] if all_lccns else 'n/a',
            "alt_lccn": all_lccns[1:],
            "oclc": all_oclcs[0] if all_oclcs else 'n/a',
            "alt_oclc": all_oclcs[1:],
        }
    except ET.ParseError as e:
        print(f"XML parsing error: {e}")
        return None

def get_lccn_from_title(title):
    encoded_title = urllib.parse.quote(title)
    url = f"http://lx2.loc.gov:210/lcdb?version=1.1&operation=searchRetrieve&query=dc.title={encoded_title}&startRecord=1&maximumRecords=5&recordSchema=mods&fo=json"
    
    try:
        response = requests.get(url)
        
        # Print the complete headers
        print("\n--- Response Headers ---")
        for header, value in response.headers.items():
            print(f"{header}: {value}")
        print("--- End Headers ---\n")
        
        print(f"Status code: {response.status_code}")
        
        # Print first part of the response
        print("\n--- Response Content Preview ---")
        print(response.text[:500] + "..." if len(response.text) > 500 else response.text)
        print("--- End Preview ---\n")
        
        # Save full response for inspection
        os.makedirs("data", exist_ok=True)
        with open("data/raw_response.txt", "w", encoding="utf-8") as f:
            f.write(response.text)
        
        # Try JSON parsing first
        try:
            data = response.json()
            # Continue with JSON processing...
        except json.JSONDecodeError:
            print("Response is not valid JSON. Attempting XML parsing...")
            # Try parsing as XML using your existing function
            xml_result = parse_xml_response(response)
            if xml_result:
                return xml_result
            else:
                print("XML parsing also failed. See data/raw_response.txt for details.")
                return {"lccn": 'n/a', "alt_lccn": [], "oclc": 'n/a', "alt_oclc": []}
        
        results = data.get("results", [])

        threshold = 80
        matches = []
        input_len = len(title.strip())
        for record in results:
            candidate_titles = []
            if "title" in record and isinstance(record["title"], str):
                candidate_titles.append(record["title"])
            if isinstance(record.get("item"), dict) and "title" in record["item"]:
                candidate_titles.append(record["item"]["title"])

            record_lccn = record.get("number_lccn", [])
            record_oclc = record.get("number_oclc", [])

            for candidate_title in candidate_titles:
                #print(f"DEBUG candidate title: '{candidate_title}'")
                norm_input = normalize(title)
                norm_candidate = normalize(candidate_title)
                # Print normalized strings for debugging
                #print(f"DEBUG norm_input: '{norm_input}', norm_candidate: '{norm_candidate}'")
                # Compare input to the start of the normalized candidate title
                score = fuzz.ratio(norm_input, norm_candidate[:len(norm_input)])
                #print(f"DEBUG score for '{candidate_title}': {score}")
                if score >= threshold:
                    matches.append({
                        "score": score,
                        "title": candidate_title,
                        "number_lccn": record_lccn,
                        "number_oclc": record_oclc
                    })

        if matches:
            # Sort matches by score descending
            matches.sort(key=lambda x: x["score"], reverse=True)
            #print("DEBUG: All matches and their LCCNs:")
            #for m in matches:
                #print(f"  Title: {m['title']}, LCCN: {m['number_lccn']}, Score: {m['score']}")
            best = matches[0]
            alt_lccn = []
            alt_oclc = []
            # Collect alternate LCCNs/OCLCs from other matches
            for m in matches[1:]:
                alt_lccn.extend([l for l in m.get("number_lccn", []) if l not in alt_lccn and l not in best.get("number_lccn", [])])
                alt_oclc.extend([o for o in m.get("number_oclc", []) if o not in alt_oclc and o not in best.get("number_oclc", [])])
            lccn_list = best.get("number_lccn", [])
            oclc_list = best.get("number_oclc", [])
            lccn = lccn_list[0] if lccn_list else 'n/a'
            oclc = oclc_list[0] if oclc_list else 'n/a'
            return {
                "lccn": lccn,
                "alt_lccn": alt_lccn,
                "oclc": oclc,
                "alt_oclc": alt_oclc
            }
        return {
            "lccn": 'n/a',
            "alt_lccn": [],
            "oclc": 'n/a',
            "alt_oclc": []
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            "lccn": 'n/a',
            "alt_lccn": [],
            "oclc": 'n/a',
            "alt_oclc": []
        }

def normalize(s):
    # Lowercase, remove punctuation, collapse whitespace
    return re.sub(r'\W+', '', s.strip().lower())

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python test2_get_lccn_from_title.py \"Book Title Here\"")
        sys.exit(1)
    title = " ".join(sys.argv[1:])
    result = get_lccn_from_title(title)
    print(f"LCCN: {result['lccn']}")
    print(f"Alt LCCN: {result['alt_lccn']}")
    print(f"OCLC: {result['oclc']}")
    print(f"Alt OCLC: {result['alt_oclc']}")