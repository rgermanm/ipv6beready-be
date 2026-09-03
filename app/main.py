from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import close as close_db
from app.db import connect as connect_db
from app.db import ping as ping_db
from app.repositories.labs import seed_labs
from app.repositories.instances import ensure_indexes as ensure_instance_indexes
from app.repositories.users import ensure_indexes as ensure_user_indexes
from app.routers import auth, console, labs, sessions


@asynccontextmanager
async def lifespan(_app: FastAPI):
    mongo_ok = connect_db()
    if mongo_ok:
        seed_labs()
        ensure_user_indexes()
        ensure_instance_indexes()
    yield
    close_db()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Backend API for IPv6BeReady container labs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(labs.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(console.router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    mongo_ok = ping_db()
    return {
        "status": "ok" if mongo_ok else "degraded",
        "mongodb": "ok" if mongo_ok else "error",
    }
