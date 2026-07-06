from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import admin, public

app = FastAPI(title="LoopLink")

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
