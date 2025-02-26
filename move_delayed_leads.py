

import sqlite3
from datetime import datetime, timedelta

DB_FILE = "seloger_properties.db"

def move_delayed_leads():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    current_time = datetime.now()
    cursor.execute("SELECT * FROM delayed_leads")
    delayed_leads = cursor.fetchall()

    if not delayed_leads:
        conn.close()
        return {"message": "No delayed leads found."}

    leads_moved = []
    leads_pending = []

    for lead in delayed_leads:
        stored_timestamp = datetime.strptime(lead[8], "%Y-%m-%d %H:%M:%S")
        time_difference = current_time - stored_timestamp
        remaining_time = timedelta(hours=24) - time_difference

        lead_details = {
            "phone_number": lead[0],
            "property_id": lead[1],
            "image_url": lead[2],
            "description": lead[3],
            "address": lead[4],
            "price": lead[5],
            "website_name": lead[6],
            "expired": lead[7],
            "timestamp": lead[8]
        }

        if time_difference >= timedelta(hours=24):
            cursor.execute("""
            INSERT OR IGNORE INTO properties (property_id, phone_number, image_url, description, address, price, website_name, expired)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                lead[1], lead[0], lead[2], lead[3], lead[4], lead[5], lead[6], lead[7]
            ))

            cursor.execute("DELETE FROM delayed_leads WHERE phone_number = ?", (lead[0],))

            lead_details["status"] = "Moved"
            leads_moved.append(lead_details)
        else:
            lead_details["status"] = "Pending"
            lead_details["remaining_time"] = str(remaining_time)
            leads_pending.append(lead_details)

    conn.commit()
    conn.close()

    return {
        "leads_moved": leads_moved,
        "leads_pending": leads_pending
    }

# Vercel Serverless Handler
def handler(request):
    result = move_delayed_leads()
    return {"status": "success", "data": result}
