from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

from .database import init_db
from .routers import mediciones


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Maceta Inteligente API",
    version="1.0.0",
    description="Logger de sensores para lirio de paz — ESP32 → Railway",
    lifespan=lifespan,
)

app.include_router(mediciones.router)


@app.get("/health", tags=["estado"])
def health():
    return {"status": "ok"}
