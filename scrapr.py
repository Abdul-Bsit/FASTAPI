import sqlite3
import requests
from bs4 import BeautifulSoup
import random
import time
from fake_useragent import UserAgent
import re

# Define base URLs
BASE_URL = "https://www.seloger-construire.com"
LISTING_URL = f"{BASE_URL}/projet-construction/maison-terrain/pays/france"
DB_FILE = "seloger_properties.db"  # SQLite database file

# Proxy list (Rotating Proxies)
PROXY_LIST = [
    "http://8598bdc273a3fa603e70:ea0531b98630b3e6@gw.dataimpulse.com:823",
    "http://8598bdc273a3fa603e70:ea0531b98630b3e6@gw.dataimpulse.com:823",
    "http://8598bdc273a3fa603e70:ea0531b98630b3e6@gw.dataimpulse.com:823"
]

# Function to get a random User-Agent
def get_headers():
    ua = UserAgent()
    return {
        "User-Agent": ua.random,
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive"
    }

# Function to get a random proxy
def get_proxy():
    return {"http": random.choice(PROXY_LIST), "https": random.choice(PROXY_LIST)}

# Create SQLite database and tables
def create_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS properties (
        property_id TEXT PRIMARY KEY,
        phone_number TEXT,
        image_url TEXT,
        description TEXT,
        address TEXT,
        price TEXT,
        website_name TEXT,
        expired BOOLEAN
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        phone_number TEXT PRIMARY KEY
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS delayed_leads (
        phone_number TEXT PRIMARY KEY,
        property_id TEXT,
        image_url TEXT,
        description TEXT,
        address TEXT,
        price TEXT,
        website_name TEXT,
        expired BOOLEAN,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

# Load existing property IDs to avoid duplicates
def load_existing_property_ids():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT property_id FROM properties")
    existing_ids = {row[0] for row in cursor.fetchall()}
    conn.close()
    return existing_ids

# Extract property ID from URL
def extract_property_id(detail_url):
    match = re.search(r'/(\d+)/$', detail_url)
    return match.group(1) if match else "N/A"

# Scrape details of a single property
def scrape_detail_page(detail_url):
    headers = get_headers()
    proxy = get_proxy()
    try:
        response = requests.get(detail_url, headers=headers, proxies=proxy, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        property_id = extract_property_id(detail_url)
        phone_number_tag = soup.find('a', class_='phoneBtnInlineNumberLink')
        phone_number = phone_number_tag['href'].replace('tel:', '').strip() if phone_number_tag else "N/A"
        image_tag = soup.find('li', class_='detailAnnonceCarouselItem')
        image_url = image_tag['data-src'] if image_tag and 'data-src' in image_tag.attrs else "N/A"
        description_div = soup.find('div', class_='detailAnnonceDescriptionContent')
        description = description_div.get_text(strip=True) if description_div else "N/A"
        location_tag = soup.find('span', class_='detailAnnonceInfosCity')
        address = location_tag.get_text(strip=True) if location_tag else "N/A"
        price_tag = soup.find('p', class_='detailAnnonceInfosPrice')
        price = re.search(r'[\d\s]+€', price_tag.get_text(strip=True)).group().replace(" ", "") if price_tag else "N/A"

        return {
            "property_id": property_id,
            "phone_number": phone_number,
            "image_url": image_url,
            "description": description,
            "address": address,
            "price": price,
            "website_name": "Seloger",
            "expired": False
        }
    except Exception as e:
        print(f"❌ Error scraping {detail_url}: {e}")
        return None

# Save a single lead to the database immediately
def save_lead(property_data):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        phone_number = property_data["phone_number"]
        
        # Check if phone number is new
        cursor.execute("SELECT phone_number FROM leads WHERE phone_number = ?", (phone_number,))
        if not cursor.fetchone():
            # Insert into leads and properties
            cursor.execute("INSERT INTO leads (phone_number) VALUES (?)", (phone_number,))
            cursor.execute("""
            INSERT INTO properties 
            (property_id, phone_number, image_url, description, address, price, website_name, expired)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                property_data["property_id"],
                phone_number,
                property_data["image_url"],
                property_data["description"],
                property_data["address"],
                property_data["price"],
                property_data["website_name"],
                property_data["expired"]
            ))
            print(f"✅ New lead saved: {phone_number}")
        else:
            # Insert into delayed_leads
            cursor.execute("""
            INSERT INTO delayed_leads 
            (phone_number, property_id, image_url, description, address, price, website_name, expired)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                phone_number,
                property_data["property_id"],
                property_data["image_url"],
                property_data["description"],
                property_data["address"],
                property_data["price"],
                property_data["website_name"],
                property_data["expired"]
            ))
            print(f"⚠️ Existing lead moved to delayed: {phone_number}")
        
        conn.commit()
    except sqlite3.IntegrityError:
        print(f"⚠️ Skipped duplicate property: {property_data['property_id']}")
    except Exception as e:
        print(f"❌ Database error: {e}")
    finally:
        conn.close()

# Main scraping logic
def scrape_all_pages():
    create_db()
    existing_ids = load_existing_property_ids()
    current_url = LISTING_URL
    page_number = 1
    leads_count = 0
    max_leads = 600

    while current_url and leads_count < max_leads:
        print(f"\n📄 Processing Page {page_number}: {current_url}")
        
        try:
            response = requests.get(current_url, headers=get_headers(), proxies=get_proxy(), timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract all property links on the page
            listings = soup.find_all('a', class_='AnnounceCard_announceCardSlider__CaJaL')
            for listing in listings:
                if leads_count >= max_leads:
                    print("🎯 Reached 600 leads. Stopping.")
                    return
                
                detail_link = listing.get('href')
                if not detail_link:
                    continue
                
                detail_url = f"{BASE_URL.rstrip('/')}{detail_link.strip()}"
                property_id = extract_property_id(detail_url)
                
                if property_id not in existing_ids:
                    property_data = scrape_detail_page(detail_url)
                    if property_data:
                        save_lead(property_data)
                        existing_ids.add(property_id)
                        leads_count += 1
                        print(f"🔄 Leads processed: {leads_count}/{max_leads}")
                        time.sleep(random.uniform(1, 3))  # Respectful delay
            
            # Find next page
            next_page = soup.find('a', {'data-testid': 'gsl.uilib.Paging.nextButton'})
            current_url = f"{BASE_URL.rstrip('/')}{next_page['href']}" if next_page else None
            page_number += 1
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Page {page_number} failed: {e}. Moving to the next page.")
            # Skip to the next page
            page_number += 1
            current_url = f"{LISTING_URL}?page={page_number}"  # Adjust URL for next page
            continue
        except Exception as e:
            print(f"❌ Unexpected error on page {page_number}: {e}. Moving to the next page.")
            page_number += 1
            current_url = f"{LISTING_URL}?page={page_number}"  # Adjust URL for next page
            continue

    print(f"\n🏁 Total leads scraped: {leads_count}")

def run_scraper():
 
    scrape_all_pages()  # Scrape and save all properties
   
if __name__ == "__main__":
    run_scraper()
