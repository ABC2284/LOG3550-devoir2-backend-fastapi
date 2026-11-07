"""Application FastAPI : CORS, routeurs et démarrage."""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from app.database import charger_livres_depart, creer_tables, engine
from app.routers import livres

# Seule l'origine du frontend est autorisée (jamais « * »).
ORIGINES_AUTORISEES = os.getenv(
    "ORIGINES_AUTORISEES", "http://localhost:5500,http://127.0.0.1:5500"
).split(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Au démarrage : créer les tables, puis charger les livres de départ si la table est vide."""
    creer_tables()
    with Session(engine) as session:
        charger_livres_depart(session)
    yield


app = FastAPI(
    title="API Bibliothèque ISTEAH",
    description="API REST du catalogue de bibliothèque (LOG3550, devoir 2) : "
                "gestion des livres avec validation, SQLite et tests automatiques.",
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Livres", "description": "Consulter, créer, modifier et supprimer des livres."},
        {"name": "Santé", "description": "Vérifier que l'API répond."},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINES_AUTORISEES,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
    expose_headers=["Location"],
)

app.include_router(livres.router)


@app.get("/sante", tags=["Santé"], summary="Vérifier l'état de l'API",
         description="Retourne `{\"statut\": \"ok\"}` quand l'API fonctionne.")
def sante():
    return {"statut": "ok"}
