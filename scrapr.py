import requests
from bs4 import BeautifulSoup
import random
import time
from fake_useragent import UserAgent
import re
from pymongo import MongoClient
from datetime import datetime, timedelta

# MongoDB Atlas connection
MONGO_URI = "mongodb+srv://abdullbasit7446:3JiTkQl8ErTFOiP2@seloger1.5hxkg.mongodb.net/?retryWrites=true&w=majority&appName=seloger1"
client = MongoClient(MONGO_URI)
db = client["seloger_db"]
properties_collection = db["properties"]
leads_collection = db["leads"]
delayed_leads_collection = db["delayed_leads"]

# Define base URLs
BASE_URL = "https://www.seloger-construire.com"
LISTING_URL = f"{BASE_URL}/projet-construction/maison-terrain/pays/france"

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
    """Automatically saves the lead when the scraper finds a new one."""
    try:
        phone_number = property_data["phone_number"]

        # Check existing leads in delayed_leads
        existing_delayed_leads = list(delayed_leads_collection.find({"phone_number": phone_number}))
        count = len(existing_delayed_leads) + 1  # Start at 1 instead of 0
        
        # Apply exponential delay in hours
        delay_hours = 24 * (2 ** (count - 1))  # 1st time = 24h, 2nd time = 48h, 3rd time = 96h
        expiration_date = datetime.now() + timedelta(hours=delay_hours)
        property_data["expiration_date"] = expiration_date

        # If phone number is NOT in leads, save in properties
        existing_lead = leads_collection.find_one({"phone_number": phone_number})
        
        if not existing_lead:
            # Insert into leads and properties
            leads_collection.insert_one({"phone_number": phone_number, "expiration_date": expiration_date})
            properties_collection.insert_one(property_data)
            print(f"✅ New lead saved: {phone_number}")
            
        else:
            # Move duplicate to delayed_leads
            delayed_leads_collection.insert_one(property_data)
            print(f"⚠️ Existing lead moved to delayed for {delay_hours} hours: {phone_number}")

    except Exception as e:
        print(f"❌ Database error: {e}")
# Main scraping logic
def scrape_all_pages():
    existing_ids = {prop['property_id'] for prop in properties_collection.find({}, {'property_id': 1})}
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
                    return {"status": "success", "message": "Reached 600 leads"}
                
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

    return {"status": "success", "message": f"Total leads scraped: {leads_count}"}
