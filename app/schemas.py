from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models import SentimentEnum, ResponseStatusEnum


# ---------- Property schemas ----------

class PropertyCreate(BaseModel):
    name: str
    city: Optional[str] = None


class PropertyOut(BaseModel):
    id: str
    name: str
    city: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Review schemas ----------

class ReviewCreate(BaseModel):
    property_id: str
    source: str = Field(..., examples=["google", "yelp", "manual"])
    rating: int = Field(..., ge=1, le=5)
    text: str


class ReviewOut(BaseModel):
    id: str
    property_id: str
    source: str
    rating: int
    text: str
    sentiment: Optional[SentimentEnum]
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Review Response schemas ----------

class ReviewResponseOut(BaseModel):
    id: str
    review_id: str
    draft_text: str
    final_text: Optional[str]
    status: ResponseStatusEnum
    drafted_at: datetime
    confirmed_at: Optional[datetime]

    class Config:
        from_attributes = True


class ConfirmResponseRequest(BaseModel):
    final_text: Optional[str] = None  # if None, use draft_text as-is
    

class SignupRequest(BaseModel):
    company_name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"