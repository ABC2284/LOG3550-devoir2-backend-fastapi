"""Moteur SQLite, session fournie par dépendance et données de départ."""
import os
from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Categorie, Livre

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bibliotheque.db")

# check_same_thread=False : FastAPI traite les requêtes dans plusieurs threads.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

LIVRES_DEPART = [
    ("Gouverneurs de la rosée", "Jacques Roumain", 1944, Categorie.roman, True),
    ("Compère Général Soleil", "Jacques Stephen Alexis", 1955, Categorie.roman, False),
    ("Le Petit Prince", "Antoine de Saint-Exupéry", 1943, Categorie.roman, True),
    ("Une brève histoire du temps", "Stephen Hawking", 1988, Categorie.science, True),
    ("Cosmos", "Carl Sagan", 1980, Categorie.science, False),
    ("Les Jacobins noirs", "C. L. R. James", 1938, Categorie.histoire, True),
    ("Sapiens : une brève histoire de l'humanité", "Yuval Noah Harari", 2011, Categorie.histoire, True),
    ("Clean Code", "Robert C. Martin", 2008, Categorie.informatique, True),
    ("The Pragmatic Programmer", "Andrew Hunt et David Thomas", 1999, Categorie.informatique, False),
    ("Éloge de la créolité", "Bernabé, Chamoiseau, Confiant", 1989, Categorie.autre, True),
]


def creer_tables() -> None:
    """Crée les tables au démarrage si elles n'existent pas."""
    SQLModel.metadata.create_all(engine)


def charger_livres_depart(session: Session) -> None:
    """Insère les livres de départ seulement si la table est vide."""
    if session.exec(select(Livre)).first() is not None:
        return
    for titre, auteur, annee, categorie, disponible in LIVRES_DEPART:
        session.add(Livre(titre=titre, auteur=auteur, annee=annee, categorie=categorie, disponible=disponible))
    session.commit()


def get_session() -> Iterator[Session]:
    """Dépendance FastAPI : une session par requête, fermée à la fin."""
    with Session(engine) as session:
        yield session
