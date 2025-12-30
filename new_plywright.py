from playwright.sync_api import sync_playwright
import json

def extract_with_playwright_only(page):
    data = {}
    
    # Find all potential section headers (orange boxed <td> with "Details" etc.)
    header_locators = page.locator("td:has-text('Details'), td:has-text('Covers'), td:has-text('Information'), td:has-text('Instruments')")
    
    print(f"Found {header_locators.count()} potential sections")
    
    for i in range(header_locators.count()):
        header_elem = header_locators.nth(i)
        full_header_text = header_elem.text_content().strip()
        
        # Clean section name (remove extra after comma or [brackets])
        section_name = full_header_text.split(',')[0].split('[')[0].strip()
        
        if not section_name:
            continue
        
        print(f"Processing section: {section_name}")
        
        # Get the parent table of the header
        parent_table = header_elem.locator("xpath=ancestor::table[1]")
        
        # Try to find the data table (next sibling or same)
        data_table = parent_table.locator("xpath=following-sibling::table[1]")
        if data_table.count() == 0:
            data_table = parent_table  # Fallback to same table
        
        if data_table.count() == 0:
            continue
        
        table_elem = data_table.first
        
        # First, try key-value extraction (most sections)
        kv_data = {}
        rows = table_elem.locator("tr")
        current_key = None
        
        for j in range(rows.count()):
            row = rows.nth(j)
            cells = row.locator("td")
            cell_count = cells.count()
            
            if cell_count == 2:
                key = cells.nth(0).text_content().strip().rstrip(":").strip()
                value = cells.nth(1).text_content().strip()
                if key:
                    kv_data[key] = value
                    current_key = key
            elif cell_count == 1 and current_key:
                extra = cells.nth(0).text_content().strip()
                if extra:
                    kv_data[current_key] += " " + extra
        
        if kv_data:
            data[section_name] = kv_data
            continue
        
        # If not key-value, try tabular data (multi-row with headers)
        tabular_data = []
        if rows.count() >= 2:
            header_row = rows.nth(0)
            header_cells = header_row.locator("td, th")
            headers = [header_cells.nth(k).text_content().strip() for k in range(header_cells.count())]
            
            if headers:
                for j in range(1, rows.count()):  # Skip header
                    row = rows.nth(j)
                    cells = row.locator("td")
                    if cells.count() == len(headers):
                        row_dict = {}
                        for k in range(len(headers)):
                            row_dict[headers[k]] = cells.nth(k).text_content().strip()
                        tabular_data.append(row_dict)
        
        if tabular_data:
            data[section_name] = tabular_data
        elif not kv_data:
            # Fallback: raw text of the table
            data[section_name] = table_elem.text_content(strip=True)
    
    return data

def scrape_tender_pure_playwright(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # False to see what's happening!
        page = browser.new_page()
        
        page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        
        print(f"Going to: {url}")
        page.goto(url)
        page.wait_for_load_state("networkidle")
        
        # Debug: Screenshot and title
        print("Page title:", page.title())
        page.screenshot(path="playwright_debug_screenshot.png")
        print("Screenshot saved - check if it shows tender details or error!")
        
        extracted_data = extract_with_playwright_only(page)
        
        browser.close()
    
    return extracted_data

# === HOW TO USE ===
# 1. Open browser -> https://mahatenders.gov.in/nicgep/app
# 2. Click any tender title in the list
# 3. IMMEDIATELY copy the new URL
# 4. Paste here and run FAST:

url = "https://mahatenders.gov.in/nicgep/app?component=%24DirectLink&page=FrontEndLatestActiveTenders&service=direct&session=T&sp=Snrmrdvnsc9i50BLybgChRA%3D%3D"

data = scrape_tender_pure_playwright(url)

print("\nExtracted Data:")
print(json.dumps(data, indent=4, ensure_ascii=False))

with open("tender_playwright_only.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("\nSaved to tender_playwright_only.json")
