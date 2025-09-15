import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

def clean_country_name(country):
    # Remove "Islamic Republic of" prefix for Afghanistan
    if country.startswith("Islamic Republic of"):
        country = country.replace("Islamic Republic of", "").strip()
    
    return country

def scrape_iso_codes():
    url = "https://en.wikipedia.org/wiki/ISO_3166-1_alpha-3"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }
    
    time.sleep(1)
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find all li elements with ISO codes
    iso_codes = {}
    
    # Look for li elements that contain monospaced spans (ISO codes)
    li_elements = soup.find_all('li')
    
    for li in li_elements:
        code_span = li.find('span', class_='monospaced')
        country_link = li.find('a')
        
        if code_span and country_link:
            code = code_span.get_text().strip()
            country = country_link.get_text().strip()
            
            # Clean country name
            country = clean_country_name(country)
            
            if len(code) == 3 and code.isupper(): 
                iso_codes[country] = code
    
    print(f"Scraped {len(iso_codes)} ISO codes")
    return iso_codes

def scrape_countries_data():
    url = "https://en.wikipedia.org/wiki/List_of_countries_and_territories_by_the_United_Nations_geoscheme"
    
    # Headers to mimic a real browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }
    

    time.sleep(1)
    
    # Send GET request with headers
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    # Parse HTML
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Try different ways to find the table
    table = None
    
    # Method 1: Try the specific class
    table = soup.find('table', class_='wikitable sortable')
    
    # Method 2: If not found, try just wikitable
    if not table:
        table = soup.find('table', class_='wikitable')
        print("Found table with just 'wikitable' class")
    
    # Method 3: Find all wikitables and look for the right one
    if not table:
        tables = soup.find_all('table', class_=lambda x: x and 'wikitable' in x)
        print(f"Found {len(tables)} wikitables")
        
        # Look for table with country data (should have rows with id attributes)
        for i, tbl in enumerate(tables):
            tbody = tbl.find('tbody')
            if tbody:
                rows_with_id = tbody.find_all('tr', id=True)
                if len(rows_with_id) > 10:  # Should have many country rows
                    table = tbl
                    print(f"Using table {i+1} with {len(rows_with_id)} country rows")
                    break
    
    if not table:
        print("Could not find the countries table!")
        return []
    
    countries_data = []
    
    # Process each row in tbody
    tbody = table.find('tbody')
    if not tbody:
        print("No tbody found, trying to find rows directly in table")
        rows = table.find_all('tr')
    else:
        rows = tbody.find_all('tr')
    
    print(f"Found {len(rows)} total rows")
    
    processed_count = 0
    for row in rows:
        # Skip header rows and rows without id
        if not row.get('id'):
            continue
            
        cells = row.find_all('td')
        if len(cells) < 4:
            continue
            
        try:
            # Extract data from each column
            # Column 1: Country name
            country_cell = cells[0]
            country_link = country_cell.find('a')
            if country_link:
                country = country_link.get_text().strip()
            else:
                country = country_cell.get_text().strip()
            
            # Clean the country name
            country = clean_country_name(country)
            
            # Column 2: Region  
            region_cell = cells[1]
            region_link = region_cell.find('a')
            if region_link:
                region = region_link.get_text().strip()
            else:
                region = region_cell.get_text().strip()
            
            # Column 4: Continent
            continent_cell = cells[3]
            continent_link = continent_cell.find('a')
            if continent_link:
                continent = continent_link.get_text().strip()
            else:
                continent = continent_cell.get_text().strip()
            
            # Special handling for Antarctica - treat as both continent and region
            if country == 'Antarctica':
                continent = 'Antarctica'
                region = 'Antarctica'
            
            # Only add if we have all required data
            if country and continent and region:
                countries_data.append({
                    'Country': country,
                    'Continent': continent, 
                    'Region': region
                })
                processed_count += 1
                if processed_count <= 5:  # Print first 5 for debugging
                    print(f"Processed: {country} | {continent} | {region}")
            
        except Exception as e:
            print(f"Error processing row {row.get('id', 'unknown')}: {e}")
            continue
    
    antarctica_exists = any(country['Country'] == 'Antarctica' for country in countries_data)
    if not antarctica_exists:
        countries_data.append({
            'Country': 'Antarctica',
            'Continent': 'Antarctica',
            'Region': 'Antarctica'
        })
        print("Added Antarctica manually")
    
    print(f"Successfully processed {len(countries_data)} countries")
    return countries_data

def create_csv_file(countries_data, iso_codes, filename='scraped_countries.csv'):
    if not countries_data:
        print("No data to save!")
        return None
        
    # Create DataFrame
    df = pd.DataFrame(countries_data)
    
    # Add ISO codes
    df['Code'] = df['Country'].map(iso_codes)
    
    if 'Antarctica' in df['Country'].values:
        antarctica_idx = df[df['Country'] == 'Antarctica'].index[0]
        if pd.isna(df.loc[antarctica_idx, 'Code']):
            df.loc[antarctica_idx, 'Code'] = 'ATA'  # Standard code for Antarctica
    
    # Reorder columns to match Countries.csv format
    df = df[['Country', 'Code', 'Continent', 'Region']]
    
    # Custom sorting function to handle special cases
    def sort_key(country):
        # Special case for Afghanistan - should be first
        if country == 'Afghanistan':
            return 'A' + chr(0)  # Ensures Afghanistan is first
        # Special case for Åland Islands - should be second
        elif country == 'Åland Islands':
            return 'A' + chr(1)  # Ensures Åland Islands is second
        # For all other countries, use normal alphabetical sorting
        else:
            return country
    
    # Sort with custom key
    df['sort_key'] = df['Country'].apply(sort_key)
    df = df.sort_values('sort_key')
    df = df.drop('sort_key', axis=1)
    
    # Report missing codes
    missing_codes = df[df['Code'].isna()]
    if not missing_codes.empty:
        print(f"\nWarning: {len(missing_codes)} countries missing ISO codes:")
        for country in missing_codes['Country']:
            print(f"  - {country}")
    
    df.to_csv(filename, index=False)
    print(f"Created {filename} with {len(df)} countries")
    
    return df

if __name__ == "__main__":
    
    print("Scraping ISO codes...")
    iso_codes = scrape_iso_codes()
    
    
    print("Scraping Wikipedia countries data...")
    countries_data = scrape_countries_data()
    
    if countries_data:
        df = create_csv_file(countries_data, iso_codes)
        
        if df is not None:
            # Display first few rows
            print("\nFirst 10 rows:")
            print(df.head(10))
            
            print(f"\nTotal countries scraped: {len(df)}")
    else:
        print("No data was scraped.")