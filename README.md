# LoopLink Campaign Builder & Distribution

A two-sided campaign tool: internal staff build and launch campaigns via a web UI; shoppers enroll by visiting a QR-linked page on their phone.

## Prerequisites

- Docker (with Compose v2) — for the Postgres database
- Python 3.12+ (3.14 recommended; project uses `uv`)
- Node 18+

---

## Local dev setup

### 1. Database

Start Postgres in Docker (port **5433** on the host):

```bash
docker compose up -d db
```

Default connection string (already baked into the backend):
```
postgresql+psycopg2://looplink:looplink@localhost:5433/looplink
```

Override via env var if needed:
```bash
export DATABASE_URL="postgresql+psycopg2://looplink:looplink@localhost:5433/looplink"
```

---

### 2. Backend

#### Option A — `uv` (recommended)

```bash
cd backend
uv sync                         # creates .venv and installs all deps
uv run alembic upgrade head     # run migrations (required before first start)
uv run uvicorn app.main:app --reload
```

#### Option B — plain `pip`

```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

| URL | Purpose |
|-----|---------|
| `http://localhost:8000` | REST API |
| `http://localhost:8000/docs` | Interactive Swagger UI |
| `http://localhost:8000/redoc` | ReDoc |

> **After pulling new migrations** always re-run `alembic upgrade head` before restarting the server.

---

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

| URL | Purpose |
|-----|---------|
| `http://localhost:5173/admin` | Admin / campaign builder UI |
| `http://localhost:5173/c/<token>` | Public shopper page |

The Vite dev server proxies nothing — it talks directly to `http://localhost:8000`. Make sure the backend is running first.

---

### 4. Full stack via Docker Compose (alternative)

Runs DB + backend + frontend together:

```bash
docker compose up
```

Same URLs apply. Hot-reload works for both services via volume mounts.

---

## Try both surfaces

1. Open `http://localhost:5173/admin` — the campaign list is empty.
2. Click **New campaign**, fill in a name, set a start and end date in the future, add at least one offer (e.g. "Product % discount → 10% off → All drinks"), and click **Create campaign**.
3. On the detail page the campaign is in **draft** state. Click **Launch now** to make it live immediately (or **Schedule** to mark it scheduled first).
4. Once live, a **Distribution** block appears with the public link and a QR code. Copy the link or scan the QR.
   - To test on a real phone: replace `localhost` with your machine's LAN IP (e.g. `http://192.168.1.x:5173/c/<token>`), or use browser devtools mobile viewport on desktop.
5. The public page shows the campaign name, offers, and an enroll form. Enter a phone number or email and click **Get my offers** — you'll see a confirmation.
6. Enroll again with the same email (different casing is fine) — you'll get the "Welcome back" message instead of a duplicate entry.
7. Go back to the admin detail and click **End campaign**.
8. Refresh the public link — it now shows "This campaign has ended."
