import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from carebridge.app.routers import voice

load_dotenv()

app = FastAPI(
    title="CareBridge API",
    description="Post-discharge readmission agent backend",
    version="1.0.0"
)

# Allow frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# E3 routers (voice agent)
app.include_router(voice.router)

# E2 routers (your endpoints — uncomment as you build them on Day 2)
# from carebridge.app.routers import patients, discharges, calls
# app.include_router(patients.router)
# app.include_router(discharges.router)
# app.include_router(calls.router)

@app.get("/health")
async def health():
    return {"status": "ok", "db": "connected", "scheduler": "running"}

@app.get("/")
async def root():
    return {"message": "CareBridge API is running"}