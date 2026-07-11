from sqlalchemy.orm import Session
from app import models


def compute_property_score(property_id: str, db: Session) -> tuple[float, int]:
    reviews = db.query(models.Review).filter(models.Review.property_id == property_id).all()

    if not reviews:
        return 0.0, 0

    avg_rating = sum(r.rating for r in reviews) / len(reviews)
    score = round((avg_rating / 5) * 100, 2)

    return score, len(reviews)