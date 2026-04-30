import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from carebridge.app.routers import voice, patients, discharges, calls
from carebridge.app.scheduler import start_scheduler, scheduler
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs on startup
    start_scheduler()
    yield
    # Runs on shutdown
    scheduler.shutdown()

app = FastAPI(
    title="CareBridge API",
    description="Post-discharge readmission agent backend",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(voice.router)
app.include_router(patients.router)
app.include_router(discharges.router)
app.include_router(calls.router)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"message": "CareBridge API is running"}