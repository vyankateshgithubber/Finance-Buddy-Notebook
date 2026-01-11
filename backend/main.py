from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from database import init_db, get_all_transactions, get_category_totals
from agents import process_chat
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


app = FastAPI(title="FrugalAgent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with specific origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB on startup
@app.on_event("startup")
def startup_event():
    logger.info("Starting up application and initializing database...")
    init_db()
    logger.info("Database initialized.")

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

@app.get("/")
def read_root():
    logger.info("Root endpoint accessed")
    return {"message": "FrugalAgent API is running"}

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    logger.info(f"Chat endpoint called. Message: {request.message}")
    try:
        response_text = await process_chat(request.message)
        logger.info("Chat processed successfully")
        return {"response": response_text}
    except Exception as e:
        logger.error(f"Error in chat_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/transactions")
def get_transactions_endpoint():
    logger.info("Transactions endpoint accessed")
    try:
        data = get_all_transactions()
        logger.info(f"Returning {len(data) if data else 0} transactions")
        return data
    except Exception as e:
        logger.error(f"Error in get_transactions_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/insights")
def get_insights_endpoint():
    logger.info("Insights endpoint accessed")
    try:
        data = get_category_totals()
        logger.info("Returning category totals")
        return data
    except Exception as e:
        logger.error(f"Error in get_insights_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
def get_stats_endpoint():
    logger.info("Stats endpoint accessed")
    try:
        from database import get_dashboard_stats
        data = get_dashboard_stats()
        logger.info("Returning dashboard stats")
        return data
    except Exception as e:
        logger.error(f"Error in get_stats_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
