import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Text, Integer, Float, DateTime, ForeignKey, Enum as SqlEnum, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class SentimentEnum(str, enum.Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


class ResponseStatusEnum(str, enum.Enum):
    draft = "draft"
    confirmed = "confirmed"

class Company(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    users = relationship("User", back_populates="company", cascade="all, delete-orphan")
    properties = relationship("Property", back_populates="company", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    company_id = Column(UUID(as_uuid=False), ForeignKey("companies.id"), nullable=False)
    email = Column(String, nullable=False, unique=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    company = relationship("Company", back_populates="users")


class Property(Base):
    __tablename__ = "properties"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    company_id = Column(UUID(as_uuid=False), ForeignKey("companies.id"), nullable=False)  # NEW
    name = Column(String, nullable=False)
    city = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    company = relationship("Company", back_populates="properties")  # NEW
    reviews = relationship("Review", back_populates="property", cascade="all, delete-orphan")
    scores = relationship("PropertyScore", back_populates="property", cascade="all, delete-orphan")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    property_id = Column(UUID(as_uuid=False), ForeignKey("properties.id"), nullable=False)
    source = Column(String, nullable=False)
    source_review_id = Column(String, nullable=True)
    rating = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    sentiment = Column(SqlEnum(SentimentEnum), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    property = relationship("Property", back_populates="reviews")
    response = relationship(
        "ReviewResponse",
        back_populates="review",
        uselist=False,
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("source", "source_review_id", name="uq_source_review"),
    )

class ReviewResponse(Base):
    __tablename__ = "review_responses"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    review_id = Column(UUID(as_uuid=False), ForeignKey("reviews.id"), nullable=False, unique=True)
    draft_text = Column(Text, nullable=False)
    final_text = Column(Text, nullable=True)
    status = Column(SqlEnum(ResponseStatusEnum), default=ResponseStatusEnum.draft, nullable=False)
    drafted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    confirmed_at = Column(DateTime(timezone=True), nullable=True)

    review = relationship("Review", back_populates="response")


class PropertyScore(Base):
    __tablename__ = "property_scores"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    property_id = Column(UUID(as_uuid=False), ForeignKey("properties.id"), nullable=False)
    score = Column(Float, nullable=False)
    review_count = Column(Integer, nullable=False)
    computed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    property = relationship("Property", back_populates="scores")