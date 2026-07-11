from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.deps import get_current_user
from app.services.scoring_service import compute_property_score

router = APIRouter(tags=["scores"])


def _get_owned_property(property_id: str, current_user: models.User, db: Session) -> models.Property:
    prop = db.query(models.Property).filter(
        models.Property.id == property_id,
        models.Property.company_id == current_user.company_id,
    ).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    return prop


@router.post("/properties/{property_id}/compute-score", response_model=schemas.PropertyScoreOut)
def compute_score(
    property_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _get_owned_property(property_id, current_user, db)

    score, review_count = compute_property_score(property_id, db)

    score_entry = models.PropertyScore(
        property_id=property_id,
        score=score,
        review_count=review_count,
    )
    db.add(score_entry)
    db.commit()
    db.refresh(score_entry)
    return score_entry


@router.get("/properties/{property_id}/score", response_model=schemas.PropertyScoreOut)
def get_latest_score(
    property_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _get_owned_property(property_id, current_user, db)

    latest = (
        db.query(models.PropertyScore)
        .filter(models.PropertyScore.property_id == property_id)
        .order_by(models.PropertyScore.computed_at.desc())
        .first()
    )
    if not latest:
        raise HTTPException(status_code=404, detail="No score computed yet for this property")
    return latest


@router.get("/properties/{property_id}/score-history", response_model=List[schemas.PropertyScoreOut])
def get_score_history(
    property_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _get_owned_property(property_id, current_user, db)

    return (
        db.query(models.PropertyScore)
        .filter(models.PropertyScore.property_id == property_id)
        .order_by(models.PropertyScore.computed_at.asc())
        .all()
    )


@router.get("/properties/rankings", response_model=List[schemas.PropertyRankingOut])
def get_rankings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    properties = db.query(models.Property).filter(
        models.Property.company_id == current_user.company_id
    ).all()

    rankings = []
    for prop in properties:
        latest = (
            db.query(models.PropertyScore)
            .filter(models.PropertyScore.property_id == prop.id)
            .order_by(models.PropertyScore.computed_at.desc())
            .first()
        )
        rankings.append(schemas.PropertyRankingOut(
            property_id=prop.id,
            property_name=prop.name,
            score=latest.score if latest else None,
            review_count=latest.review_count if latest else 0,
        ))

    rankings.sort(key=lambda r: (r.score is not None, r.score), reverse=True)
    return rankings