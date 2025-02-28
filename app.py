from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Literal
from pydantic import BaseModel
from scraper import scrape_all_pages
from contextlib import asynccontextmanager
import os
from bson import ObjectId


MONGO_URI = os.getenv("MONGO_URI")  # Load from environment variable
client = MongoClient(MONGO_URI)
db = client["seloger_db"]
properties_collection = db["properties"]
leads_collection = db["leads"]
delayed_leads_collection = db["delayed_leads"]

app = FastAPI(lifespan=lifespan)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    if properties_collection is None:
        raise HTTPException(status_code=500, detail="MongoDB connection not initialized")
    leads_count = properties_collection.count_documents({})
    return {"status": "success", "leads_count": leads_count}

@app.post("/leads")
async def get_leads():
    """Retrieve all scraped leads."""
    if properties_collection is None:
        raise HTTPException(status_code=500, detail="MongoDB connection not initialized")
    leads = list(properties_collection.find({}, {"_id": 0}))
    return {"status": "success", "leads": leads}

@app.get("/delayed-leads")
async def get_delayed_leads():
    """Retrieve all delayed leads."""
    if delayed_leads_collection is None:
        raise HTTPException(status_code=500, detail="MongoDB connection not initialized")
    delayed_leads = list(delayed_leads_collection.find({}, {"_id": 0}))
    return {"status": "success", "delayed_leads": delayed_leads}

@app.get("/today-leads")
def get_today_new_leads():
    """Fetch leads added today based on expiration_date - 7 days."""
    if leads_collection is None:
        raise HTTPException(status_code=500, detail="MongoDB connection not initialized")
    try:
        now = datetime.now(timezone.utc)
        start_of_day = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        end_of_day = start_of_day.replace(hour=23, minute=59, second=59)

        # Leads where expiration_date is exactly 7 days from today
        today_new_leads = list(leads_collection.find({
            "expiration_date": {
                "$gte": start_of_day + timedelta(days=7),
                "$lte": end_of_day + timedelta(days=7)
            }
        }))

        # Convert ObjectId to string for JSON response
        for lead in today_new_leads:
            lead["_id"] = str(lead["_id"])

        return {"count": len(today_new_leads), "leads": today_new_leads}

    except Exception as e:
        return {"error": str(e)}

def move_expired_delayed_leads():
    """Moves expired delayed leads to the main leads collection."""
    if delayed_leads_collection is None or leads_collection is None or properties_collection is None:
        raise HTTPException(status_code=500, detail="MongoDB connection not initialized")
    try:
        now = datetime.now(timezone.utc)

        expired_leads = list(delayed_leads_collection.find({"expiration_date": {"$lt": now}}))

        if not expired_leads:
            return {"status": "no expired leads", "moved_leads": []}

        moved_leads = []  # Store details of moved leads

        for lead in expired_leads:
            phone_number = lead.get("phone_number")

            # Check if already exists in main collection
            if leads_collection.find_one({"phone_number": phone_number}):
                continue  # Skip duplicates

            # Set a new expiration date (7 days from now)
            lead["expiration_date"] = now + timedelta(days=7)

            # Insert into leads collection
            leads_collection.insert_one({"phone_number": phone_number, "expiration_date": lead["expiration_date"]})

            # Insert into properties collection (full details)
            properties_collection.insert_one(lead)

            moved_leads.append(lead)  # Append full lead details

            # Remove from delayed collection
            delayed_leads_collection.delete_one({"_id": lead["_id"]})

        return {"status": "success", "moved_leads": moved_leads}

    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/move_delayed_leads/")
async def move_delayed_leads():
    """API endpoint to move expired delayed leads."""
    result = move_expired_delayed_leads()
    return result

def remove_expired_leads():
    """Removes leads from both collections when their 7-day expiration has passed."""
    if leads_collection is None or properties_collection is None:
        raise HTTPException(status_code=500, detail="MongoDB connection not initialized")
    try:
        now = datetime.now(timezone.utc)

        # Find expired leads in leads_collection
        expired_leads = list(leads_collection.find({"expiration_date": {"$lt": now}}))

        if not expired_leads:
            return {"status": "no expired leads", "deleted_leads": []}

        deleted_leads = []

        for lead in expired_leads:
            phone_number = lead.get("phone_number")
            
            # Delete from leads_collection
            leads_collection.delete_one({"_id": lead["_id"]})
            
            # Delete from properties_collection
            properties_collection.delete_one({"phone_number": phone_number})

            deleted_leads.append(phone_number)

        return {"status": "success", "deleted_leads": deleted_leads}

    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/remove_expired_leads/")
async def remove_expired_leads_endpoint():
    """API endpoint to remove expired leads from the database."""
    result = remove_expired_leads()
    return result

# Export the FastAPI app for Vercel
handler = app
