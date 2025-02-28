from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import JSONResponse 
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
from typing import List, Dict , Literal
from pydantic import BaseModel
from scraper import scrape_all_pages
from contextlib import asynccontextmanager
import json
from bson import ObjectId
import threading
import os
app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB Atlas connection
MONGO_URI = "mongodb+srv://abdullbasit7446:3JiTkQl8ErTFOiP2@seloger1.5hxkg.mongodb.net/?retryWrites=true&w=majority&appName=seloger1"
client = MongoClient(MONGO_URI)
db = client["seloger_db"]
properties_collection = db["properties"]
leads_collection = db["leads"]
delayed_leads_collection = db["delayed_leads"]

# 🏗️ FastAPI Endpoints
@app.get("/start-scraper")
async def start_scraper(background_tasks: BackgroundTasks):
    """Starts the scraper in the background."""
    background_tasks.add_task(scrape_all_pages)
    return {"message": "Scraper started in the background"}

# Health check endpoint
@app.get("/")
async def health_check():
    return {"status": "Hello from Seloger Scrapper API"}

@app.get("/scraping-status")
async def scraping_status():
    """Check the number of scraped leads."""
    leads_count = properties_collection.count_documents({})
    return {"status": "success", "leads_count": leads_count}

@app.get("/leads")
async def get_leads():
    """Retrieve all scraped leads."""
    leads = list(properties_collection.find({}, {"_id": 0}))
    return {"status": "success", "leads": leads}

@app.get("/delayed-leads")
async def get_delayed_leads():
    """Retrieve all delayed leads."""
    delayed_leads = list(delayed_leads_collection.find({}, {"_id": 0}))
    return {"status": "success", "delayed_leads": delayed_leads}

@app.get("/today-leads")
def get_today_new_leads():
    """Fetch leads added today based on expiration_date - 7 days."""
    try:
        now = datetime.now(timezone.utc)
        start_of_day = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        end_of_day = start_of_day.replace(hour=23, minute=59, second=59)

        today_new_leads = list(leads_collection.find({
            "expiration_date": {
                "$gte": start_of_day + timedelta(days=7),
                "$lte": end_of_day + timedelta(days=7)
            }
        }))

        for lead in today_new_leads:
            lead["_id"] = str(lead["_id"])

        return {"count": len(today_new_leads), "leads": today_new_leads}
    except Exception as e:
        return {"error": str(e)}

def move_expired_delayed_leads():
    """Moves expired delayed leads to the main leads collection."""
    try:
        now = datetime.now(timezone.utc)
        expired_leads = list(delayed_leads_collection.find({"expiration_date": {"$lt": now}}))
        if not expired_leads:
            return {"status": "no expired leads", "moved_leads": []}

        moved_leads = []
        for lead in expired_leads:
            phone_number = lead.get("phone_number")
            if leads_collection.find_one({"phone_number": phone_number}):
                continue
            lead["expiration_date"] = now + timedelta(days=7)
            leads_collection.insert_one({"phone_number": phone_number, "expiration_date": lead["expiration_date"]})
            properties_collection.insert_one(lead)
            moved_leads.append(lead)
            delayed_leads_collection.delete_one({"_id": lead["_id"]})
        return {"status": "success", "moved_leads": moved_leads}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def move_delayed_leads_thread():
    threading.Thread(target=move_expired_delayed_leads).start()

@app.post("/move_delayed_leads/")
async def move_delayed_leads():
    """API endpoint to move expired delayed leads."""
    move_delayed_leads_thread()
    return {"status": "processing"}

def remove_expired_leads():
    """Removes leads from both collections when their 7-day expiration has passed."""
    now = datetime.now(timezone.utc)
    expired_leads = list(leads_collection.find({"expiration_date": {"$lt": now}}))
    if not expired_leads:
        return {"status": "no expired leads", "deleted_leads": []}
    deleted_leads = []
    for lead in expired_leads:
        phone_number = lead.get("phone_number")
        leads_collection.delete_one({"_id": lead["_id"]})
        properties_collection.delete_one({"phone_number": phone_number})
        deleted_leads.append(phone_number)
    return {"status": "success", "deleted_leads": deleted_leads}

def remove_expired_leads_thread():
    threading.Thread(target=remove_expired_leads).start()

@app.post("/remove_expired_leads/")
async def remove_expired_leads_endpoint():
    """API endpoint to remove expired leads from the database."""
    remove_expired_leads_thread()
    return {"status": "processing"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))  # Koyeb provides the PORT env variable
    uvicorn.run(app, host="0.0.0.0", port=port)
