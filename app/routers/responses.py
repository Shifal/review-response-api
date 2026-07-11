from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.services.llm_service import draft_response

router = APIRouter()


@router.post("/reviews/{review_id}/draft-response", response_model=schemas.ReviewResponseOut)
def create_draft_response(review_id: str, db: Session = Depends(get_db)):
    review = db.query(models.Review).filter(models.Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review.response:
        raise HTTPException(status_code=400, detail="A response already exists for this review")

    draft_text = draft_response(review.text, review.rating)

    response = models.ReviewResponse(
        review_id=review_id,
        draft_text=draft_text,
        status=models.ResponseStatusEnum.draft,
    )
    db.add(response)
    db.commit()
    db.refresh(response)
    return response


@router.get("/reviews/{review_id}/response", response_model=schemas.ReviewResponseOut)
def get_response(review_id: str, db: Session = Depends(get_db)):
    response = db.query(models.ReviewResponse).filter(models.ReviewResponse.review_id == review_id).first()
    if not response:
        raise HTTPException(status_code=404, detail="No response found for this review")
    return response


@router.patch("/reviews/{review_id}/response", response_model=schemas.ReviewResponseOut)
def edit_draft_response(review_id: str, payload: schemas.ConfirmResponseRequest, db: Session = Depends(get_db)):
    response = db.query(models.ReviewResponse).filter(models.ReviewResponse.review_id == review_id).first()
    if not response:
        raise HTTPException(status_code=404, detail="No response found for this review")
    if response.status == models.ResponseStatusEnum.confirmed:
        raise HTTPException(status_code=400, detail="Cannot edit a confirmed response")

    if payload.final_text:
        response.draft_text = payload.final_text

    db.commit()
    db.refresh(response)
    return response


@router.post("/reviews/{review_id}/confirm-response", response_model=schemas.ReviewResponseOut)
def confirm_response(review_id: str, payload: schemas.ConfirmResponseRequest, db: Session = Depends(get_db)):
    response = db.query(models.ReviewResponse).filter(models.ReviewResponse.review_id == review_id).first()
    if not response:
        raise HTTPException(status_code=404, detail="No response found for this review")
    if response.status == models.ResponseStatusEnum.confirmed:
        raise HTTPException(status_code=400, detail="Response already confirmed")

    response.final_text = payload.final_text if payload.final_text else response.draft_text
    response.status = models.ResponseStatusEnum.confirmed
    response.confirmed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(response)
    return response