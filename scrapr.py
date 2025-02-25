# import sqlite3
# import requests
# from bs4 import BeautifulSoup
# import random
# import time
# from fake_useragent import UserAgent
# import re
# import os

# # Define base URLs
# BASE_URL = "https://www.seloger-construire.com"
# LISTING_URL = f"{BASE_URL}/projet-construction/maison-terrain/pays/france"
# DB_FILE = "seloger_properties.db"  # SQLite database file

# # Proxy list (Rotating Proxies)
# PROXY_LIST = [
#     "http://8598bdc273a3fa603e70:ea0531b98630b3e6@gw.dataimpulse.com:823",
#     "http://8598bdc273a3fa603e70:ea0531b98630b3e6@gw.dataimpulse.com:823",
#     "http://8598bdc273a3fa603e70:ea0531b98630b3e6@gw.dataimpulse.com:823"
# ]

# # Function to get a random User-Agent
# def get_headers():
#     ua = UserAgent()
#     return {
#         "User-Agent": ua.random,
#         "Accept-Language": "en-US,en;q=0.9",
#         "Referer": "https://www.google.com/",
#         "Connection": "keep-alive"
#     }

# # Function to get a random proxy
# def get_proxy():
#     return {"http": random.choice(PROXY_LIST), "https": random.choice(PROXY_LIST)}

# # Create SQLite database and tables (if not already created)
# # Modify the delayed_leads table creation to include a timestamp column
# def create_db():
#     conn = sqlite3.connect(DB_FILE)
#     cursor = conn.cursor()

#     # Create properties table if it does not exist
#     cursor.execute("""
#     CREATE TABLE IF NOT EXISTS properties (
#         property_id TEXT PRIMARY KEY,
#         phone_number TEXT,
#         image_url TEXT,
#         description TEXT,
#         address TEXT,
#         price TEXT,
#         website_name TEXT,
#         expired BOOLEAN
#     )
#     """)

#     # Create leads table to store new phone numbers
#     cursor.execute("""
#     CREATE TABLE IF NOT EXISTS leads (
#         phone_number TEXT PRIMARY KEY
#     )
#     """)

#     # Create delayed_leads table to store phone numbers already found with timestamp
#     cursor.execute("""
#     CREATE TABLE IF NOT EXISTS delayed_leads (
#         phone_number TEXT PRIMARY KEY,
#         property_id TEXT,
#         image_url TEXT,
#         description TEXT,
#         address TEXT,
#         price TEXT,
#         website_name TEXT,
#         expired BOOLEAN,
#         timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
#     )
#     """)

#     conn.commit()
#     conn.close()


# # Load existing property_id values from the database
# def load_existing_property_ids():
#     conn = sqlite3.connect(DB_FILE)
#     cursor = conn.cursor()
#     cursor.execute("SELECT property_id FROM properties")
#     existing_ids = {row[0] for row in cursor.fetchall()}
#     conn.close()
#     return existing_ids

# # Extract property_id from the detail page URL
# def extract_property_id(detail_url):
#     match = re.search(r'/(\d+)/$', detail_url)
#     return match.group(1) if match else "N/A"

# # Scrape property details from a detail page
# def scrape_detail_page(detail_url):
#     headers = get_headers()
#     proxy = get_proxy()

#     print(f"   ➜ Scraping Detail Page: {detail_url}")

#     try:
#         response = requests.get(detail_url, headers=headers, proxies=proxy, timeout=15)
#         response.raise_for_status()
#         soup = BeautifulSoup(response.text, "html.parser")

#         # Extract Property ID
#         property_id = extract_property_id(detail_url)

#         # Extract phone number
#         phone_number_tag = soup.find('a', class_='phoneBtnInlineNumberLink')
#         phone_number = phone_number_tag['href'].replace('tel:', '').strip() if phone_number_tag else "N/A"

#         # Extract image URL
#         image_tag = soup.find('li', class_='detailAnnonceCarouselItem')
#         image_url = image_tag['data-src'] if image_tag and 'data-src' in image_tag.attrs else "N/A"

#         # Extract description
#         description_div = soup.find('div', class_='detailAnnonceDescriptionContent')
#         description = description_div.get_text(strip=True) if description_div else "N/A"

#         # Extract address
#         location_tag = soup.find('span', class_='detailAnnonceInfosCity')
#         address = location_tag.get_text(strip=True) if location_tag else "N/A"

#         # Extract price
#         price_tag = soup.find('p', class_='detailAnnonceInfosPrice')
#         extracted_price = "N/A"
#         if price_tag:
#             price_text = price_tag.get_text(strip=True)
#             match = re.search(r'[\d\s]+€', price_text)  # Extracts numbers followed by €
#             extracted_price = match.group().replace(" ", "") if match else "N/A"

#         return {
#             "property_id": property_id,
#             "phone_number": phone_number,
#             "image_url": image_url,
#             "description": description,
#             "address": address,
#             "price": extracted_price,
#             "website_name": "Seloger",
#             "expired": False  # Leads are fresh initially
#         }

#     except requests.exceptions.RequestException as e:
#         print(f"❌ Error scraping detail page {detail_url}: {e}")
#         return None

# # Check if phone number already exists in the database
# def check_phone_number_exists(phone_number):
#     conn = sqlite3.connect(DB_FILE)
#     cursor = conn.cursor()
#     cursor.execute("SELECT phone_number FROM leads WHERE phone_number = ?", (phone_number,))
#     result = cursor.fetchone()
#     conn.close()
#     return result is not None

# # Save property data to appropriate table (leads or delayed_leads)
# def save_to_db(property_data):
#     conn = sqlite3.connect(DB_FILE)
#     cursor = conn.cursor()

#     phone_number = property_data["phone_number"]

#     if not check_phone_number_exists(phone_number):
#         # If phone number not found in leads, insert it into leads table and save to properties
#         cursor.execute("INSERT INTO leads (phone_number) VALUES (?)", (phone_number,))
#         cursor.execute("""
#         INSERT OR IGNORE INTO properties (property_id, phone_number, image_url, description, address, price, website_name, expired)
#         VALUES (?, ?, ?, ?, ?, ?, ?, ?)
#         """, (
#             property_data["property_id"],
#             property_data["phone_number"],
#             property_data["image_url"],
#             property_data["description"],
#             property_data["address"],
#             property_data["price"],
#             property_data["website_name"],
#             property_data["expired"]
#         ))
#     else:
#         # If phone number exists, move to delayed_leads
#         cursor.execute("""
#         INSERT OR IGNORE INTO delayed_leads (phone_number, property_id, image_url, description, address, price, website_name, expired)
#         VALUES (?, ?, ?, ?, ?, ?, ?, ?)
#         """, (
#             property_data["phone_number"],
#             property_data["property_id"],
#             property_data["image_url"],
#             property_data["description"],
#             property_data["address"],
#             property_data["price"],
#             property_data["website_name"],
#             property_data["expired"]
#         ))

#     conn.commit()
#     conn.close()

# # Scrape all listing pages and extract new property details
# def scrape_all_pages():
#     all_properties = []
#     existing_property_ids = load_existing_property_ids()  # Load stored property IDs
#     current_url = LISTING_URL
#     page_number = 1
#     max_retries = 3
#     leads_count = 0  # Variable to count the number of leads scraped
#     max_leads = 30  # Limit of leads to scrape

#     while current_url and leads_count < max_leads:
#         headers = get_headers()
#         proxy = get_proxy()

#         print(f"\n🟢 Scraping Listing Page {page_number}: {current_url}")

#         retry_attempts = 0
#         while retry_attempts < max_retries:
#             try:
#                 response = requests.get(current_url, headers=headers, proxies=proxy, timeout=15)
#                 response.raise_for_status()
#                 soup = BeautifulSoup(response.text, "html.parser")

#                 # Extract property detail page links
#                 listings = soup.find_all('a', class_='AnnounceCard_announceCardSlider__CaJaL')
#                 for listing in listings:
#                     detail_link = listing.get('href')
#                     if detail_link:
#                         detail_url = f"{BASE_URL}{detail_link}"  # Construct full URL
#                         property_id = extract_property_id(detail_url)

#                         # Check if this property is already stored
#                         if property_id not in existing_property_ids:
#                             property_details = scrape_detail_page(detail_url)
#                             if property_details:
#                                 save_to_db(property_details)  # Save to DB
#                                 all_properties.append(property_details)
#                                 leads_count += 1  # Increment the leads counter

#                                 if leads_count >= max_leads:  # Check if we have scraped the required number of leads
#                                     print("\n✅ Reached 600 leads. Scraping complete.")
#                                     return  # Stop scraping

#                     time.sleep(random.uniform(2, 5))  # Delay to avoid blocking

#                 # Find the next page link
#                 next_page_link = soup.find('a', {'data-testid': 'gsl.uilib.Paging.nextButton'})
#                 if next_page_link and 'href' in next_page_link.attrs:
#                     current_url = f"{BASE_URL}{next_page_link['href'].strip()}"
#                     page_number += 1
#                 else:
#                     print("\n✅ No more pages found. Scraping complete.")
#                     break

#                 break  # Exit retry loop if successful

#             except requests.exceptions.RequestException as e:
#                 retry_attempts += 1
#                 print(f"❌ Error scraping listing page {current_url} (Attempt {retry_attempts}/{max_retries}): {e}")

#         if retry_attempts == max_retries:
#             print(f"⚠️ Skipping Listing Page {page_number} after {max_retries} failed attempts.")
#             page_number += 1
#             current_url = f"{BASE_URL}/projet-construction/maison-terrain/pays/france?page={page_number}"

#     print("\n✅ Scraping complete.")


# # Run the scraper
# def run_scraper():
#     create_db()  # Create database and tables
#     scrape_all_pages()

# if __name__ == "__main__":
#     run_scraper()







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

# Create SQLite database and tables (if not already created)
# Modify the delayed_leads table creation to include a timestamp column
def create_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Create properties table if it does not exist
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

    # Create leads table to store new phone numbers
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        phone_number TEXT PRIMARY KEY
    )
    """)

    # Create delayed_leads table to store phone numbers already found with timestamp
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


# Load existing property_id values from the database
def load_existing_property_ids():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT property_id FROM properties")
    existing_ids = {row[0] for row in cursor.fetchall()}
    conn.close()
    return existing_ids

# Extract property_id from the detail page URL
def extract_property_id(detail_url):
    match = re.search(r'/(\d+)/$', detail_url)
    return match.group(1) if match else "N/A"

# Scrape property details from a detail page
def scrape_detail_page(detail_url):
    headers = get_headers()
    proxy = get_proxy()

    print(f"   ➜ Scraping Detail Page: {detail_url}")

    try:
        response = requests.get(detail_url, headers=headers, proxies=proxy, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract Property ID
        property_id = extract_property_id(detail_url)

        # Extract phone number
        phone_number_tag = soup.find('a', class_='phoneBtnInlineNumberLink')
        phone_number = phone_number_tag['href'].replace('tel:', '').strip() if phone_number_tag else "N/A"

        # Extract image URL
        image_tag = soup.find('li', class_='detailAnnonceCarouselItem')
        image_url = image_tag['data-src'] if image_tag and 'data-src' in image_tag.attrs else "N/A"

        # Extract description
        description_div = soup.find('div', class_='detailAnnonceDescriptionContent')
        description = description_div.get_text(strip=True) if description_div else "N/A"

        # Extract address
        location_tag = soup.find('span', class_='detailAnnonceInfosCity')
        address = location_tag.get_text(strip=True) if location_tag else "N/A"

        # Extract price
        price_tag = soup.find('p', class_='detailAnnonceInfosPrice')
        extracted_price = "N/A"
        if price_tag:
            price_text = price_tag.get_text(strip=True)
            match = re.search(r'[\d\s]+€', price_text)  # Extracts numbers followed by €
            extracted_price = match.group().replace(" ", "") if match else "N/A"

        return {
            "property_id": property_id,
            "phone_number": phone_number,
            "image_url": image_url,
            "description": description,
            "address": address,
            "price": extracted_price,
            "website_name": "Seloger",
            "expired": False  # Leads are fresh initially
        }

    except requests.exceptions.RequestException as e:
        print(f"❌ Error scraping detail page {detail_url}: {e}")
        return None

# Check if phone number already exists in the database
def check_phone_number_exists(phone_number):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT phone_number FROM leads WHERE phone_number = ?", (phone_number,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

# Preprocess the scraped data
def preprocess_data(property_data):
    # Preprocess price
    property_data["price"] = property_data["price"].replace("€", "").replace(" ", "").strip()

    # Preprocess phone number
    property_data["phone_number"] = re.sub(r"\s+", " ", property_data["phone_number"]).strip()

    # Preprocess address
    property_data["address"] = re.sub(r"\s{2,}", " ", property_data["address"]).strip()

    # Preprocess description (just in case we want to remove any unwanted characters)
    property_data["description"] = property_data["description"].strip()

    return property_data

# Save property data to appropriate table (leads or delayed_leads)
def save_to_db(property_data):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    phone_number = property_data["phone_number"]

    if not check_phone_number_exists(phone_number):
        # If phone number not found in leads, insert it into leads table and save to properties
        cursor.execute("INSERT INTO leads (phone_number) VALUES (?)", (phone_number,))
        cursor.execute("""
        INSERT OR IGNORE INTO properties (property_id, phone_number, image_url, description, address, price, website_name, expired)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            property_data["property_id"],
            property_data["phone_number"],
            property_data["image_url"],
            property_data["description"],
            property_data["address"],
            property_data["price"],
            property_data["website_name"],
            property_data["expired"]
        ))
    else:
        # If phone number exists, move to delayed_leads
        cursor.execute("""
        INSERT OR IGNORE INTO delayed_leads (phone_number, property_id, image_url, description, address, price, website_name, expired)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            property_data["phone_number"],
            property_data["property_id"],
            property_data["image_url"],
            property_data["description"],
            property_data["address"],
            property_data["price"],
            property_data["website_name"],
            property_data["expired"]
        ))

    conn.commit()
    conn.close()

# Scrape all listing pages and extract new property details
def scrape_all_pages():
    all_properties = []
    existing_property_ids = load_existing_property_ids()  # Load stored property IDs
    current_url = LISTING_URL
    page_number = 1
    max_retries = 3
    leads_count = 0  # Variable to count the number of leads scraped
    max_leads = 600  # Limit of leads to scrape

    while current_url and leads_count < max_leads:
        headers = get_headers()
        proxy = get_proxy()

        print(f"\n🟢 Scraping Listing Page {page_number}: {current_url}")

        retry_attempts = 0
        while retry_attempts < max_retries:
            try:
                response = requests.get(current_url, headers=headers, proxies=proxy, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")

                # Extract property detail page links
                listings = soup.find_all('a', class_='AnnounceCard_announceCardSlider__CaJaL')
                for listing in listings:
                    detail_link = listing.get('href')
                    if detail_link:
                        detail_url = f"{BASE_URL}{detail_link}"  # Construct full URL
                        property_id = extract_property_id(detail_url)

                        # Check if this property is already stored
                        if property_id not in existing_property_ids:
                            property_details = scrape_detail_page(detail_url)
                            if property_details:
                                # Preprocess the property data before saving it to the database
                                processed_property = preprocess_data(property_details)
                                save_to_db(processed_property)  # Save to DB
                                all_properties.append(processed_property)
                                leads_count += 1  # Increment the leads counter

                                if leads_count >= max_leads:  # Check if we have scraped the required number of leads
                                    print("\n✅ Reached 600 leads. Scraping complete.")
                                    return  # Stop scraping

                    time.sleep(random.uniform(1, 3))  # Sleep to avoid too many requests

                # Move to next page
                next_page_tag = soup.find('a', class_='paginationNext')
                current_url = f"{BASE_URL}{next_page_tag['href']}" if next_page_tag else None
                page_number += 1
                break

            except requests.exceptions.RequestException as e:
                retry_attempts += 1
                print(f"⚠️ Error occurred: {e}. Retrying... ({retry_attempts}/{max_retries})")
                time.sleep(3)  # Wait before retrying

    return all_properties  # Return the scraped properties

# Main function to run the scraper
def run_scraper():
    create_db()  # Create database and tables if not already done
    all_properties = scrape_all_pages()  # Scrape and preprocess all properties
    print(f"\n✅ Reached 600 leads. Scraping complete.")


if __name__ == "__main__":
    run_scraper()
