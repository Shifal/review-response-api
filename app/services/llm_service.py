from google import genai
from app.config import settings

_client = genai.Client(api_key=settings.gemini_api_key)

_PROMPT_TEMPLATE = """You are a professional property management representative responding to an online review.

Write a warm, professional response to this resident review. Keep it under 100 words.
- If the review is positive, thank them genuinely and invite them to reach out with anything they need.
- If the review is negative or mixed, acknowledge their concern specifically, apologize where appropriate, and state that the team wants to make it right — invite them to contact the office directly.
- Never sound robotic or generic. Reference specific details from their review.

Review (rating: {rating}/5): "{review_text}"

Write only the response text — no preamble, no labels."""


def draft_response(review_text: str, rating: int) -> str:
    prompt = _PROMPT_TEMPLATE.format(review_text=review_text, rating=rating)

    response = _client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt,
    )
    return response.text.strip()