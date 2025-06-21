# Payments API – Technical Documentation

## Overview

The Payments API is a full-stack solution for managing installment orders, wallet balances, and payment processing, with support for webhooks and a modern admin dashboard.

**Tech stack:**
- **Backend:** FastAPI, SQLAlchemy, PostgreSQL, Celery, Redis
- **Frontend:** Next.js, React, TailwindCSS
- **Other:** Docker, pytest, Stripe (for external payments)

---

## Architecture Diagram

```mermaid
graph TD
  subgraph Frontend
    FE[Next.js Dashboard]
  end
  subgraph Backend
    API[FastAPI App]
    Celery[Celery Worker]
    DB[(PostgreSQL)]
    Redis[(Redis)]
  end
  subgraph External
    Stripe[Stripe API]
    Webhook[Webhook Listener]
  end

  FE -- REST/JSON --> API
  API -- SQLAlchemy --> DB
  API -- Celery Tasks --> Celery
  Celery -- SQLAlchemy --> DB
  API -- Redis Broker --> Celery
  Celery -- Redis Broker --> API
  Celery -- Stripe API --> Stripe
  Celery -- Webhook Events --> Webhook
```

---

## Backend

### Main Technologies

- **FastAPI:** REST API framework
- **SQLAlchemy:** ORM for PostgreSQL
- **Celery:** Background task processing (scheduled charges, webhooks)
- **Redis:** Celery broker and result backend
- **Stripe:** External payment fallback
- **pytest:** Unit testing

### Key Modules

#### 1. `app/main.py`
- FastAPI app entry point
- Registers API routes for:
  - Installment orders (`/installments/orders`)
  - Wallets (`/wallets`)
  - Charges (`/charges`)
  - Webhook logs (`/webhooks`)
- CORS middleware for frontend integration

#### 2. `app/models.py`
- SQLAlchemy models:
  - `InstallmentOrder`: Represents an order split into installments
  - `Installment`: Each scheduled payment for an order
  - `Wallet`: Customer wallet with balance
  - `WalletLedger`: Transaction log for wallet
  - `Charge`: Payment attempt (wallet or external)
  - `WebhookLog`: Outbound webhook event log

#### 3. `app/schemas.py`
- Pydantic schemas for request/response validation
- Ensures type safety and API documentation

#### 4. `app/crud.py`
- CRUD operations for all models
- Encapsulates DB logic for creating, reading, updating, and deleting records

#### 5. `app/api/endpoints/installments.py`
- Endpoints for creating and managing installment orders
- Schedules background charge tasks

#### 6. `app/celery_tasks.py` & `celery_worker.py`
- Celery task definitions for:
  - Scheduling and processing charges
  - Sending webhook events
  - Periodic processing of due installments
- Integrates with Stripe for external payments

#### 7. `listeners/webhook_listener.py`
- FastAPI app to receive and log webhook events for testing

---

### Database Schema (Simplified)

- **installment_orders**: id (UUID), customer_id, amount, status, etc.
- **installments**: id (UUID), order_id (FK), due_date, status, etc.
- **wallets**: id (UUID), customer_id, balance, etc.
- **wallet_ledger**: id, wallet_id (FK), transaction_type, amount, etc.
- **charges**: id, customer_id, amount, status, payment_method, split_instructions (JSON), etc.
- **webhook_logs**: id, event_type, payload (JSON), status, etc.

---

### API Endpoints

#### Installment Orders
- `POST /installments/orders`: Create a new order with flexible schedule
- `GET /installments/orders`: List orders
- `GET /installments/orders/{order_id}`: Get order details

#### Wallets
- `POST /wallets`: Create a wallet
- `GET /wallets/{customer_id}`: Get wallet details
- `GET /wallets/{customer_id}/ledger`: Get wallet transaction history
- `POST /wallets/{customer_id}/credit`: Credit wallet

#### Charges
- `POST /charges`: Create a charge (wallet first, fallback to external)
- `GET /charges`: List charges

#### Webhooks
- `GET /webhooks`: List webhook logs

#### Health
- `GET /health`: Health check

---

### Background Tasks

- **Charge Scheduler:** Schedules and processes due installment charges
- **Webhook Events:** Sends `charge.succeeded` and `charge.failed` events to external listeners
- **Split Instructions:** Accepts and returns split instructions in charge webhooks
- **Wallet Logic:** Applies wallet balance first, then falls back to Stripe

---

## Frontend

### Main Technologies

- **Next.js:** React-based framework for SSR and static sites
- **TailwindCSS:** Utility-first CSS framework
- **Axios:** HTTP client for API calls
- **Recharts:** Charting library for dashboard

### Key Components

- **DashboardOverview:** Stats and charts for orders, wallets, revenue
- **InstallmentOrders:** Table of all installment orders
- **Wallets:** Table of all wallets and balances
- **WebhookLogs:** Table of webhook event logs

### API Integration

- Uses Axios to call backend endpoints (URL set via `NEXT_PUBLIC_API_URL`)
- Handles loading and error states
- Displays live data from backend

---

## Testing

- **Unit tests:** Located in `backend/tests/`
  - `test_routes.py`: Tests API endpoints using FastAPI's TestClient
  - `test_models.py`: Tests SQLAlchemy models and relationships using SQLite in-memory DB
- **Run tests:**  
  ```bash
  cd backend
  pytest
  ```

---

## Deployment

### Docker

- **Dockerfiles** for backend and frontend
- **docker-compose.yml** to orchestrate:
  - FastAPI backend
  - Celery worker
  - Next.js frontend
  - PostgreSQL
  - Redis

### Example Compose Command

```bash
docker-compose up --build
```

---

## Environment Variables

- `DATABASE_URL`: PostgreSQL connection string
- `CELERY_BROKER_URL`: Redis broker for Celery
- `CELERY_RESULT_BACKEND`: Redis backend for Celery
- `STRIPE_SECRET_KEY`: Stripe API key
- `WEBHOOK_URLS`: Comma-separated list of webhook endpoints
- `NEXT_PUBLIC_API_URL`: (Frontend) URL of backend API

---

## Webhook Events

- **charge.succeeded**: Sent when a charge is successful
- **charge.failed**: Sent when a charge fails
- **Payload includes:** charge details, split instructions, metadata

---

## Security

- CORS enabled for frontend-backend communication
- Passwords and secrets managed via environment variables
- All sensitive operations require proper authentication in production (add JWT or OAuth as needed)

---

## Extensibility

- Add authentication/authorization (JWT, OAuth)
- Add more payment providers
- Add more dashboard features (filters, exports)
- Add more webhook event types

---

## Getting Help

- **API docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Frontend:** [http://localhost:3000](http://localhost:3000)
- **Contact:** Project maintainer or open an issue in your repository

---

# Project Setup & Run Instructions

## Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- **PostgreSQL**
- **Redis**
- (Optional) **Docker**

---

## 1. Backend (FastAPI)

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in `backend/`:
```
DATABASE_URL=postgresql://user:password@localhost/payments_db
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
STRIPE_SECRET_KEY=your_stripe_secret_key
WEBHOOK_URLS=http://localhost:3001/api/webhook
```

Start the API server:
```bash
uvicorn app.main:app --reload
```

Start the Celery worker (in a new terminal):
```bash
cd backend
venv\Scripts\activate  # or source venv/bin/activate
celery -A celery_worker.celery_app worker --loglevel=info
```

---

## 2. Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

The dashboard will be at [http://localhost:3000](http://localhost:3000)

---

## 3. Webhook Listener (Optional)

```bash
cd listeners
pip install fastapi uvicorn "pydantic[email]"
uvicorn webhook_listener:app --host 0.0.0.0 --port 3001
```

---

## 4. Docker Compose (All-in-One)

If you want to run everything with Docker:

```bash
docker-compose up --build
```

---

## 5. Running Tests

```bash
cd backend
pytest
```

---

## 6. API Documentation

Visit [http://localhost:8000/docs](http://localhost:8000/docs) for interactive API docs.

---

## 7. Troubleshooting
- **Network errors:** Ensure backend is running and CORS is enabled.
- **Database errors:** Check your `DATABASE_URL` and that PostgreSQL is running.
- **Celery not working:** Ensure Redis is running and environment variables are correct.
- **Frontend not loading data:** Check `NEXT_PUBLIC_API_URL` in frontend `.env.local`.

---

For more details, see the code comments and each service's README. 