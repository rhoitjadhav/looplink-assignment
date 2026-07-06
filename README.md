# LoopLink Campaign Builder & Distribution

A two-sided campaign tool: internal staff build and launch campaigns via a web UI; shoppers enroll by visiting a QR-linked page on their phone.

## Prerequisites

- Docker (with Compose v2) — for the Postgres database
- Python 3.11+
- Node 18+

## Run it

### Database

```bash
docker compose up -d db
```

### Backend

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head        # must run before first start, and after any new migration
uvicorn app.main:app --reload
```

API available at `http://localhost:8000`
Interactive docs at `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Builder UI at `http://localhost:5173/admin`

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
