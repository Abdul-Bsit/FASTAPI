from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from fastapi import FastAPI, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from typing import List
from fastapi import Request
from scrapr import run_scraper
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
def fetch_data_from_db(query: str, params: tuple = ()) -> List[tuple]:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows

# Function to generate an HTML table
def generate_html_table(headers: List[str], rows: List[tuple]) -> str:
    table_html = "<table border='1'><tr>"
    for header in headers:
        table_html += f"<th>{header}</th>"
    table_html += "</tr>"
    
    for row in rows:
        table_html += "<tr>"
        for cell in row:
            table_html += f"<td>{cell}</td>"
        table_html += "</tr>"
    
    table_html += "</table>"
    return table_html

# Endpoint to trigger the scraper
@app.get("/start_scraper/")
async def start_scraper(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_scraper)
    return {"message": "Scraper has started!"}

# Get all properties
@app.get("/properties", response_class=HTMLResponse)
async def get_properties():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM properties")
    rows = cursor.fetchall()
    headers = [column[0] for column in cursor.description]
    conn.close()
    
    # Generate the HTML table with the rows and headers
    table_html = generate_html_table(headers, rows)
    return table_html

# Get all leads
@app.get("/leads", response_class=HTMLResponse)
async def get_leads():
    query = "SELECT phone_number FROM leads"
    rows = fetch_data_from_db(query)
    headers = ["Phone Number"]
    
    # Generate the HTML table
    table_html = generate_html_table(headers, rows)
    return table_html

# Get all delayed leads
@app.get("/delayed_leads", response_class=HTMLResponse)
async def get_delayed_leads():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM delayed_leads")
    rows = cursor.fetchall()
    headers = [column[0] for column in cursor.description]
    conn.close()
    
    # Generate the HTML table
    table_html = generate_html_table(headers, rows)
    return table_html

# Run FastAPI using Uvicorn (run this via command line in your terminal)
# uvicorn app:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
