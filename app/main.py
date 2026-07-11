from fastapi import FastAPI
from app.database import Base, engine
from app import models
from app.routers import reviews

app = FastAPI(title="Review Response API")

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

app.include_router(reviews.router, tags=["reviews"])

@app.get("/health")
def health_check():
    return {"status": "ok"}