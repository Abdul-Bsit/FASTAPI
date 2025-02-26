from fastapi import FastAPI, HTTPException, BackgroundTasks
from scraper import scrape_all_pages
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from datetime import datetime
from typing import List, Dict
from pydantic import BaseModel
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
MONGO_URI = os.getenv("MONGO_URI", "your-default-mongo-uri")
client = MongoClient(MONGO_URI)
db = client["seloger_db"]
properties_collection = db["properties"]
leads_collection = db["leads"]
delayed_leads_collection = db["delayed_leads"]

# FastAPI Endpoints
@app.post("/start-scraping")
async def start_scraping(background_tasks: BackgroundTasks):
    """Start the scraping process in the background."""
    background_tasks.add_task(scrape_all_pages)
    return {"status": "started", "message": "Scraping started in the background."}

@app.get("/scraping-status")
async def scraping_status():
    """Check the status of the scraping process."""
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

@app.get("/today-leads", response_model=List[Dict])
def get_today_leads():
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    leads = list(properties_collection.find({"expiration_date": {"$gte": today}}, {"_id": 0}))
    return leads

# Vercel automatically handles execution, so no need for uvicorn.run()
