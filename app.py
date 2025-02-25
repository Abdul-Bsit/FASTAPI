from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from fastapi import FastAPI, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from typing import List
from fastapi import Request
from scrapr import run_scraper
from move_delayed_leads import move_delayed_leads
# Initialize FastAPI app
app = FastAPI()

# Enable CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to a specific domain if needed
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)
# SQLite database file
DB_FILE = "seloger_properties.db"

# Pydantic models to format the data from the database
class Property(BaseModel):
    property_id: str
    phone_number: str
    image_url: str
    description: str
    address: str
    price: str
    website_name: str
    expired: bool

class Lead(BaseModel):
    phone_number: str

class DelayedLead(BaseModel):
    phone_number: str
    property_id: str
    image_url: str
    description: str
    address: str
    price: str
    website_name: str
    expired: bool


# Function to fetch data from the database
def fetch_data_from_db(query: str, params: tuple = ()) -> List[dict]:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(query, params)
    columns = [column[0] for column in cursor.description]
    rows = cursor.fetchall()
    conn.close()

    # Convert rows into list of dictionaries
    return [dict(zip(columns, row)) for row in rows]



#move delayed leads logic goes here
@app.get("/move_delayed_leads")
def trigger_move_delayed_leads():
    try:
        result = move_delayed_leads()
        return result
    except Exception as e:
        return {"error": f"An error occurred: {e}"}
    

# Endpoint to trigger the scraper
@app.get("/start_scraper/")
async def start_scraper(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_scraper)
    return {"message": "Scraper has started!"}

# Get all properties in JSON format
@app.get("/properties")
async def get_properties():
    query = "SELECT * FROM properties"
    properties = fetch_data_from_db(query)
    return properties

# Get all leads in JSON format
@app.get("/leads")
async def get_leads():
    query = "SELECT phone_number FROM leads"
    leads = fetch_data_from_db(query)
    return leads

# Get all delayed leads in JSON format
@app.get("/delayed_leads")
async def get_delayed_leads():
    query = "SELECT * FROM delayed_leads"
    delayed_leads = fetch_data_from_db(query)
    return delayed_leads

# Run FastAPI using Uvicorn (run this via command line in your terminal)
# uvicorn app:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)


