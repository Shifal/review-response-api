from google import genai
from app.config import settings
from app.models import SentimentEnum

_client = genai.Client(api_key=settings.gemini_api_key)

_PROMPT_TEMPLATE = """Classify the sentiment of this apartment resident review as exactly one word: positive, neutral, or negative.

Review: "{review_text}"

Respond with only the single word — no punctuation, no explanation."""


def classify_sentiment(review_text: str) -> SentimentEnum:
    prompt = _PROMPT_TEMPLATE.format(review_text=review_text)

    response = _client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt,
    )
    label = response.text.strip().lower()

    if label not in ("positive", "neutral", "negative"):
        label = "neutral"

    return SentimentEnum(label)