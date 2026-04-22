import os
from fastapi import FastAPI
from dotenv import load_dotenv
from app.routers import voice

load_dotenv()

app = FastAPI(
    title="Readmission Agent API",
    description="Post-discharge voice agent backend",
    version="1.0.0"
)

# Register routers
app.include_router(voice.router)

@app.get("/health")
async def health():
    return {"status": "ok", "scheduler": "running"}

@app.get("/")
async def root():
    return {"message": "Readmission Agent API is running"}