from fastapi import FastAPI
from app.database import Base, engine
from app import models
from app.routers import reviews
from app.routers import reviews, responses, auth, scores

app = FastAPI(title="Review Response API")

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(reviews.router, tags=["reviews"])
app.include_router(responses.router, tags=["responses"])
app.include_router(scores.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}