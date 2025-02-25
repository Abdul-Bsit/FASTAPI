import sqlite3
from datetime import datetime, timedelta

DB_FILE = "seloger_properties.db"
# Function to move delayed leads to properties table after 24 hours
def move_delayed_leads():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Get current timestamp
    current_time = datetime.now()

    # Find leads older than 24 hours
    cursor.execute("""
    SELECT * FROM delayed_leads WHERE timestamp < ?
    """, (current_time - timedelta(days=1),))

    delayed_leads = cursor.fetchall()

    for lead in delayed_leads:
        # Move each delayed lead to properties table
        cursor.execute("""
        INSERT OR IGNORE INTO properties (property_id, phone_number, image_url, description, address, price, website_name, expired)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            lead[1],  # property_id
            lead[0],  # phone_number
            lead[2],  # image_url
            lead[3],  # description
            lead[4],  # address
            lead[5],  # price
            lead[6],  # website_name
            lead[7],  # expired
        ))

        # Remove from delayed_leads table
        cursor.execute("""
        DELETE FROM delayed_leads WHERE phone_number = ?
        """, (lead[0],))

    conn.commit()
    conn.close()

# Run the function to move delayed leads
move_delayed_leads()
