from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

from app.services.sentiment import classify_sentiment
from app.deps import get_current_user

router = APIRouter()


# ---------- Properties ----------

@router.post("/properties", response_model=schemas.PropertyOut)
def create_property(
    payload: schemas.PropertyCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    prop = models.Property(
        company_id=current_user.company_id,
        name=payload.name,
        city=payload.city,
    )
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return prop


@router.get("/properties", response_model=List[schemas.PropertyOut])
def list_properties(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return db.query(models.Property).filter(models.Property.company_id == current_user.company_id).all()


# ---------- Reviews ----------

@router.post("/reviews", response_model=schemas.ReviewOut)
def create_review(
    payload: schemas.ReviewCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    prop = db.query(models.Property).filter(
        models.Property.id == payload.property_id,
        models.Property.company_id == current_user.company_id,
    ).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    sentiment = classify_sentiment(payload.text)

    review = models.Review(
        property_id=payload.property_id,
        source=payload.source,
        rating=payload.rating,
        text=payload.text,
        sentiment=sentiment,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


@router.get("/reviews", response_model=List[schemas.ReviewOut])
def list_reviews(
    property_id: Optional[str] = None,
    sentiment: Optional[models.SentimentEnum] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = db.query(models.Review).join(models.Property).filter(
        models.Property.company_id == current_user.company_id
    )
    if property_id:
        query = query.filter(models.Review.property_id == property_id)
    if sentiment:
        query = query.filter(models.Review.sentiment == sentiment)
    return query.offset(skip).limit(limit).all()


@router.get("/reviews/{review_id}", response_model=schemas.ReviewOut)
def get_review(review_id: str, db: Session = Depends(get_db)):
    review = db.query(models.Review).filter(models.Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review