from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import admin, public
from .scheduler import tick


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler()
    scheduler.add_job(tick, "interval", seconds=5)
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="LoopLink", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Schema is owned by Alembic — run `alembic upgrade head` before starting.
# No create_all here: one source of truth for the schema.

app.include_router(admin.router)
app.include_router(public.router)


@app.get("/api/health")
def health():
    return {"ok": True}
