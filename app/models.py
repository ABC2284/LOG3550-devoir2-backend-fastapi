"""Modèle de base de données : la table « livre »."""
from enum import Enum

from sqlmodel import Field, SQLModel


class Categorie(str, Enum):
    """Catégories autorisées pour un livre."""
    roman = "roman"
    science = "science"
    histoire = "histoire"
    informatique = "informatique"
    autre = "autre"


class Livre(SQLModel, table=True):
    """Ligne de la table « livre » (ce qui est stocké en base)."""
    id: int | None = Field(default=None, primary_key=True)
    titre: str = Field(max_length=200)
    auteur: str = Field(max_length=200)
    annee: int
    categorie: Categorie
    # unique + index : la base elle-même refuse deux fois le même ISBN (NULL multiples autorisés).
    isbn: str | None = Field(default=None, unique=True, index=True, max_length=13)
    disponible: bool = True
