from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any

from database import init_db, get_user_transactions, get_user_category_totals
from agents import process_chat
from user_context import current_user_id # Import the context variable


app = FastAPI(title="FrugalAgent Multi-User API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    init_db()

# --- Request Models ---
class ChatRequest(BaseModel):
    user_id: str = Field(..., description="Unique ID of the user")
    message: str

class ChatResponse(BaseModel):
    response: str

@app.get("/")
def read_root():
    return {"message": "FrugalAgent API is running"}

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    # SET CONTEXT: This token ensures that down the line, 
    # database.py knows which user_id is active.
    token = current_user_id.set(request.user_id)
    
    try:
        response_text = await process_chat(request.user_id, request.message)
        return {"response": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up context
        current_user_id.reset(token)

@app.get("/transactions/{user_id}")
def get_transactions_endpoint(user_id: str):
    try:
        return get_user_transactions(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/insights/{user_id}")
def get_insights_endpoint(user_id: str):
    try:
        return get_user_category_totals(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
