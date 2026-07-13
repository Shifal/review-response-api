import logging
from apscheduler.schedulers.background import BackgroundScheduler

from app.database import SessionLocal
from app import models
from app.services.scoring_service import compute_property_score

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def recompute_all_property_scores():
    db = SessionLocal()
    try:
        properties = db.query(models.Property).all()
        logger.info(f"Nightly scoring job: recomputing scores for {len(properties)} properties")

        for prop in properties:
            score, review_count = compute_property_score(prop.id, db)

            score_entry = models.PropertyScore(
                property_id=prop.id,
                score=score,
                review_count=review_count,
            )
            db.add(score_entry)

        db.commit()
        logger.info("Nightly scoring job: completed successfully")
    except Exception:
        db.rollback()
        logger.exception("Nightly scoring job failed")
    finally:
        db.close()


def start_scheduler():
    scheduler.add_job(
        recompute_all_property_scores,
        trigger="interval",
        hours=24,
        # minutes=1,
        id="nightly_score_recompute",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started: nightly score recomputation registered (every 24h)")