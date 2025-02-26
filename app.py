
from fastapi import FastAPI, HTTPException,  BackgroundTasks
from scrapr import scrape_all_pages
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from datetime import datetime
from typing import List,Dict
from datetime import datetime, timedelta
from pydantic import BaseModel


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

# FastAPI Endpoints

@app.get("/start-scraping")
async def start_scraping(background_tasks: BackgroundTasks):
    """Endpoint to start the scraping process in the background."""
    background_tasks.add_task(scrape_all_pages)
    return {"status": "started", "message": "Scraping process started in the background."}

@app.get("/scraping-status")
async def scraping_status():
    """Endpoint to check the status of the scraping process."""
    leads_count = properties_collection.count_documents({})
    return {"status": "success", "leads_count": leads_count}



@app.get("/leads")
async def get_leads():
    """Endpoint to retrieve all scraped leads."""
    leads = list(properties_collection.find({}, {"_id": 0}))
    return {"status": "success", "leads": leads}

@app.get("/delayed-leads")
async def get_delayed_leads():
    """Endpoint to retrieve all delayed leads."""
    delayed_leads = list(delayed_leads_collection.find({}, {"_id": 0}))
    return {"status": "success", "delayed_leads": delayed_leads}

@app.get("/today-leads", response_model=List[Dict])
def get_today_leads():
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    leads = list(properties_collection.find({"expiration_date": {"$gte": today}}, {"_id": 0}))
    return leads



@app.post("/move_delayed_leads")
async def move_delayed_leads():
    now = datetime.now()

    # Find leads scheduled for today
    delayed_leads = list(delayed_leads_collection.find({"expiration_date": {"$lte": now}}))

    if not delayed_leads:
        return {"message": "✅ No delayed leads to move today."}

    moved_leads = []

    for lead in delayed_leads:
        lead["_id"] = str(lead["_id"])  # Convert ObjectId to string for JSON response

        # Move lead to leads collection with new expiration date
        new_expiration_date = now + timedelta(days=7)
        lead["expiration_date"] = new_expiration_date
        leads_collection.insert_one(lead)

        # Add lead to properties collection
        properties_collection.insert_one(lead)

        # Remove from delayed_leads collection
        delayed_leads_collection.delete_one({"_id": lead["_id"]})

        moved_leads.append(lead)

    return {
        "message": "✅ Moved delayed leads",
        "moved_leads": moved_leads
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

