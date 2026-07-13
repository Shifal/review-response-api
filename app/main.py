import logging
from fastapi import FastAPI
from app.database import Base, engine
from app import models
from app.routers import reviews
from app.routers import reviews, responses, auth, scores
from app.scheduler import start_scheduler
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(title="Review Response API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    start_scheduler()

app.include_router(auth.router)
app.include_router(reviews.router, tags=["reviews"])
app.include_router(responses.router, tags=["responses"])
app.include_router(scores.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}