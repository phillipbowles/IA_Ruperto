import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from .routers import mediciones

# El esquema lo administra Alembic, que corre en el entrypoint del contenedor
# antes de levantar uvicorn. Ya no se llama a create_all(): dos mecanismos
# creando tablas es la forma más rápida de que el esquema de local y el de
# producción se separen sin que nadie se entere.

app = FastAPI(
    title="Maceta Inteligente API",
    version="1.1.0",
    description="Logger de sensores para lirio de paz — ESP32 → Railway",
)

# El front corre en otro origen (5173 en local, otro dominio en producción).
# La placa no necesita CORS: no es un navegador.
ORIGENES = [o.strip() for o in os.getenv("CORS_ORIGENES", "http://localhost:5173").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mediciones.router)


@app.get("/health", tags=["estado"])
def health():
    return {"status": "ok"}
