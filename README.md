# Review Response API

A backend service for **multifamily property reputation management** — ingesting resident reviews, classifying sentiment, generating AI-assisted responses with a mandatory human approval step, and computing a reputation score per property over time.

This project is modeled on the real-world problem faced by property management companies: reviews arrive constantly across multiple platforms, someone has to read every one, decide how to respond, and track whether the property's reputation is trending up or down. This API is a backend-only implementation of that workflow.

🔗 **Live demo:** [https://review-response-api.onrender.com/docs](https://review-response-api.onrender.com/docs)

> Hosted on Render's free tier — the service spins down after periods of inactivity, so the first request may take 30-60 seconds to respond while it wakes up. Subsequent requests are fast.

---

## Table of Contents

- [What This Project Does](#what-this-project-does)
- [Why It's Built This Way](#why-its-built-this-way)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Data Model](#data-model)
- [The AI Safety Pattern: Draft → Confirm](#the-ai-safety-pattern-draft--confirm)
- [Reputation Scoring](#reputation-scoring)
- [Multi-Tenancy & Auth](#multi-tenancy--auth)
- [API Reference](#api-reference)
- [Getting Started](#getting-started)
- [Running Tests](#running-tests)
- [Project Structure](#project-structure)
- [Future Enhancements](#future-enhancements)

---

## What This Project Does

A property management company signs up, adds their properties, and then:

1. **Ingests reviews** for each property (rating + text, from any source — Google, Yelp, manual entry, etc.)
2. **Automatically classifies sentiment** (positive / neutral / negative) on every review using Gemini
3. **Generates an AI-drafted response** to any review on request — but the draft is never sent automatically. A human must review and explicitly confirm it before it's considered final.
4. **Computes a reputation score** (0–100) per property based on its reviews, with full historical tracking so trends over time are visible
5. **Ranks properties** within a company by current reputation score

All of this is scoped per company — one management company's data is fully isolated from another's.

---

## Why It's Built This Way

Three backend design decisions in this project were made deliberately, not by default, and are worth understanding before reading the code:

**1. AI never writes directly to a "sent" state.**
Every AI-generated review response is stored as a `draft`. A separate, explicit `confirm` action — performed by a human — is the only thing that can mark a response as final. This is the single most important design decision in the project: it means a hallucinated or inappropriate AI response can never go out to a real resident without a person reading it first. See [The AI Safety Pattern](#the-ai-safety-pattern-draft--confirm) below.

**2. Reputation scores are historical records, not fields that get overwritten.**
Every time a score is computed, a *new* row is written rather than updating an existing one. This means the system can always answer "how has this property's reputation trended over the last 3 months?" — a question that matters far more in practice than "what is the score right now?"

**3. Every data-bearing table is scoped to a company at the database query level, not just the application layer.**
Multi-tenant isolation is enforced by filtering every query through `company_id`, not by trusting the client to only ask for its own data. This is tested explicitly (see [Running Tests](#running-tests)).

---

## Architecture

```
                          ┌─────────────────┐
                          │   Client (any   │
                          │  HTTP consumer) │
                          └────────┬────────┘
                                   │  Bearer JWT
                                   ▼
                          ┌─────────────────┐
                          │   FastAPI App    │
                          │  (routers layer) │
                          └────────┬────────┘
                 ┌─────────────────┼─────────────────────┐
                 ▼                 ▼                     ▼
         ┌───────────────┐ ┌───────────────┐   ┌───────────────────┐
         │  auth router  │ │ reviews router│   │ responses router  │
         │ signup/login  │ │  CRUD +       │   │ draft/edit/confirm│
         │ JWT issuance  │ │  sentiment    │   │                   │
         └───────┬───────┘ └───────┬───────┘   └─────────┬─────────┘
                 │                 │                     │
                 ▼                 ▼                     ▼
         ┌───────────────┐ ┌───────────────┐   ┌───────────────────┐
         │ auth_service  │ │sentiment.py   │   │  llm_service.py   │
         │ bcrypt + JWT  │ │(Gemini call)  │   │  (Gemini call)     │
         └───────────────┘ └───────────────┘   └───────────────────┘
                 │                 │                     │
                 └─────────────────┼─────────────────────┘
                                   ▼
                          ┌─────────────────┐
                          │   PostgreSQL     │
                          │   (Supabase)     │
                          └─────────────────┘

                     ┌────────────────────┐
                     │   scores router     │
                     │ compute/get/history │
                     │      /rankings      │
                     └──────────┬──────────┘
                                ▼
                     ┌────────────────────┐
                     │  scoring_service.py │
                     │ (pure aggregation,  │
                     │   no external call) │
                     └────────────────────┘
```

Every router depends on `get_current_user` (in `app/deps.py`), which decodes the JWT and attaches the authenticated user — and by extension, their `company_id` — to the request. Every query in `reviews`, `properties`, and `scores` filters through that `company_id`.

---

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Framework | FastAPI | Async-capable, automatic OpenAPI/Swagger docs, strong typing via Pydantic |
| Database | PostgreSQL (Supabase, Session Pooler) | Relational integrity for a clearly relational domain (companies → properties → reviews) |
| ORM | SQLAlchemy | Explicit models, relationships, and query control |
| Auth | JWT (`python-jose`) + `bcrypt` | Stateless auth, standard password hashing |
| AI | Google Gemini (`gemini-3.5-flash`) via `google-genai` | Free-tier accessible, fast, sufficient for classification and short-form drafting |
| Scheduling | APScheduler (in-process `BackgroundScheduler`) | Runs nightly score recomputation without needing separate worker infrastructure |
| Testing | `pytest` + FastAPI `TestClient` | Fast, no external test infra required |

---

## Data Model

```
Company (1) ──< (many) User
Company (1) ──< (many) Property
Property (1) ──< (many) Review
Property (1) ──< (many) PropertyScore
Review (1) ──< (1) ReviewResponse
```

| Table | Key columns | Notes |
|---|---|---|
| `companies` | `id`, `name` | The tenant. Every property and user belongs to exactly one. |
| `users` | `id`, `company_id`, `email` (unique), `hashed_password` | Auth identity. |
| `properties` | `id`, `company_id`, `name`, `city` | A single apartment community. |
| `reviews` | `id`, `property_id`, `source`, `source_review_id` (nullable), `rating` (1–5), `text`, `sentiment` (nullable until classified) | Ingested feedback. `(source, source_review_id)` has a unique constraint, enforced at the database level, so re-ingesting the same external review (e.g. from a nightly pull) never creates a duplicate — the endpoint returns the existing record instead. Manually-entered reviews simply omit `source_review_id`. |
| `review_responses` | `id`, `review_id` (unique — one response per review), `draft_text`, `final_text` (nullable), `status` (`draft`/`confirmed`), `confirmed_at` | The draft→confirm audit trail. |
| `property_scores` | `id`, `property_id`, `score`, `review_count`, `computed_at` | One row per computation — history is preserved, never overwritten. |

---

## The AI Safety Pattern: Draft → Confirm

This is the core interesting piece of the project, worth explaining explicitly.

```
POST /reviews/{id}/draft-response
   → Gemini generates a suggested reply
   → Stored with status = "draft", final_text = null
   → NOTHING is considered "sent" at this point

PATCH /reviews/{id}/response   (optional)
   → A human can edit the draft text before approving it
   → Blocked once status = "confirmed"

POST /reviews/{id}/confirm-response
   → A human explicitly approves (as-is, or with edits)
   → status flips to "confirmed", confirmed_at is set
   → This is the only action that produces a final, approved response
```

Guarantees enforced at the API level (not just documented — actually tested):
- A review can only ever have **one** response record (`review_id` is a unique foreign key) — calling `draft-response` twice on the same review returns a `400`.
- A confirmed response **cannot be edited** — `PATCH` returns a `400` if `status == confirmed`.
- A response **cannot be confirmed twice** — the second call returns a `400`.

---

## Reputation Scoring

The current scoring model is intentionally simple and fully explainable:

```
score = (average_rating_of_all_reviews / 5) * 100
```

Each time a score is computed, it's recalculated from all reviews currently on the property and stored as a **new row** in `property_scores` — never overwriting a previous score. This means `GET /properties/{id}/score-history` always shows the full trend, and `GET /properties/rankings` can always answer "which of my properties is doing best right now" using only the latest row per property.

Scores are computed two ways:
- **On demand** — `POST /properties/{id}/compute-score`, for a single property immediately
- **Automatically, every 24 hours** — a background job (`app/scheduler.py`, built with APScheduler) loops through every property across every company and recomputes its score, reusing the exact same `compute_property_score()` function as the manual endpoint. There's a single source of truth for the scoring logic regardless of which path triggers it.

This scoring formula itself is a deliberately simple v1. See [Future Enhancements](#future-enhancements) for the planned recency-weighted, confidence-adjusted version.

---

## Multi-Tenancy & Auth

- Signup (`POST /auth/signup`) creates a `Company` and its first `User` together, in a single transaction, and returns a JWT immediately — no separate login step needed right after signup.
- Every protected endpoint requires `Authorization: Bearer <token>`.
- The JWT payload carries both `sub` (user id) and `company_id`. Every query that touches `properties`, `reviews`, or `scores` filters by the requesting user's `company_id` — a user from Company A can never read or write Company B's data, even by guessing IDs.
- This isolation is directly tested in `tests/test_multitenancy.py`.

---

## API Reference

### Auth
| Method | Path | Description |
|---|---|---|
| POST | `/auth/signup` | Create a company + user, returns JWT |
| POST | `/auth/login` | Authenticate an existing user, returns JWT |

### Properties
| Method | Path | Description |
|---|---|---|
| POST | `/properties` | Create a property (scoped to your company) |
| GET | `/properties` | List your company's properties |

### Reviews
| Method | Path | Description |
|---|---|---|
| POST | `/reviews` | Add a review; sentiment is classified automatically |
| GET | `/reviews` | List reviews, filterable by `property_id`, `sentiment`; paginated |
| GET | `/reviews/{id}` | Get a single review |

### Responses
| Method | Path | Description |
|---|---|---|
| POST | `/reviews/{id}/draft-response` | Generate an AI draft reply |
| GET | `/reviews/{id}/response` | Retrieve the current response record |
| PATCH | `/reviews/{id}/response` | Edit the draft (only while status = draft) |
| POST | `/reviews/{id}/confirm-response` | Approve and finalize the response |

### Scores
| Method | Path | Description |
|---|---|---|
| POST | `/properties/{id}/compute-score` | Recalculate and store a new score |
| GET | `/properties/{id}/score` | Get the latest score |
| GET | `/properties/{id}/score-history` | Full score history, chronological |
| GET | `/properties/rankings` | All your properties, ranked by latest score |

Full interactive documentation is available at `/docs` (Swagger UI) once the server is running.

---

## Getting Started

### Prerequisites
- Python 3.11+
- A PostgreSQL database (this project was built against Supabase's Session Pooler connection)
- A Gemini API key from [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

### Setup

```bash
git clone https://github.com/YOUR_USERNAME/review-response-api.git
cd review-response-api

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
DATABASE_URL=postgresql://<user>:<password>@<host>:5432/postgres
GEMINI_API_KEY=your_gemini_api_key
JWT_SECRET_KEY=a_long_random_secret
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
```

Generate a secure `JWT_SECRET_KEY` with:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Run

```bash
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` for interactive Swagger documentation. Tables are created automatically on startup.

---

## Running Tests

```bash
pytest -v
```

Current coverage:
- Sentiment classification (positive and negative cases)
- The full draft → confirm response lifecycle
- The one-response-per-review and no-edit-after-confirm guarantees
- Multi-tenant data isolation between two separate companies
- Rejection of unauthenticated requests
- Idempotent ingestion — re-submitting a review with the same `(source, source_review_id)` returns the existing record rather than creating a duplicate

> Note: tests call the live Gemini API for sentiment/drafting, so a full run takes roughly 1-2 minutes and requires a valid `GEMINI_API_KEY`.

---

## Project Structure

```
review-response-api/
├── app/
│   ├── main.py                  # FastAPI app, startup, router registration
│   ├── database.py              # SQLAlchemy engine/session setup
│   ├── models.py                 # ORM models: Company, User, Property, Review, ReviewResponse, PropertyScore
│   ├── schemas.py                # Pydantic request/response models
│   ├── config.py                 # Environment-based settings
│   ├── deps.py                   # get_current_user auth dependency
│   ├── scheduler.py               # APScheduler: nightly automated score recomputation
│   ├── routers/
│   │   ├── auth.py               # signup, login
│   │   ├── reviews.py            # properties + reviews CRUD
│   │   ├── responses.py          # draft/edit/confirm
│   │   └── scores.py             # compute/get/history/rankings
│   └── services/
│       ├── auth_service.py       # password hashing, JWT issuance/verification
│       ├── sentiment.py          # Gemini sentiment classification
│       ├── llm_service.py        # Gemini response drafting
│       └── scoring_service.py    # score computation logic
├── tests/
│   ├── conftest.py               # shared fixtures (client, auth, sample data)
│   ├── test_sentiment.py
│   ├── test_response_flow.py
│   ├── test_multitenancy.py
│   └── test_idempotency.py
├── pytest.ini
├── requirements.txt
├── .env.example
└── README.md
```

---

## Future Enhancements

Deliberately scoped out of v1 to keep the build focused, but worth noting as planned next steps:

- **Recency-weighted, confidence-adjusted scoring** — weight recent reviews more heavily via exponential decay, and pull scores from low-volume properties toward a neutral midpoint until enough reviews accumulate to be statistically meaningful.
- **Rate limiting on AI endpoints** — protect the Gemini free-tier quota from being exhausted by rapid repeated calls.
- **Bulk review import** — CSV/JSON batch ingestion endpoint for onboarding a property's historical review backlog in one call.