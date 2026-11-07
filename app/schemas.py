"""Schémas Pydantic : ce que l'API reçoit et renvoie (distincts de la table en base)."""
import re
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import Categorie

ANNEE_MIN = 1450
CHAMPS_NON_NULLABLES = ("titre", "auteur", "annee", "categorie", "disponible")


def verifier_annee(valeur: int | None) -> int | None:
    """L'année doit être comprise entre 1450 et l'année en cours."""
    if valeur is None:
        return valeur
    annee_courante = date.today().year
    if not ANNEE_MIN <= valeur <= annee_courante:
        raise ValueError(f"L'année doit être comprise entre {ANNEE_MIN} et {annee_courante}.")
    return valeur


def normaliser_isbn(valeur: str | None) -> str | None:
    """Accepte « 978-2-07-040850-4 » ; garde seulement les chiffres (10 ou 13)."""
    if valeur is None:
        return valeur
    nettoye = valeur.replace("-", "").replace(" ", "")
    if not re.fullmatch(r"[0-9]{10}|[0-9]{13}", nettoye):
        raise ValueError("L'ISBN doit contenir exactement 10 ou 13 chiffres.")
    return nettoye


class LivreCreate(BaseModel):
    """Corps de POST et de PUT : tous les champs du livre, sans identifiant."""
    # extra="forbid" : un « id » envoyé par le client est refusé (422), jamais accepté.
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
        json_schema_extra={"examples": [{
            "titre": "Gouverneurs de la rosée", "auteur": "Jacques Roumain", "annee": 1944,
            "categorie": "roman", "isbn": "9782070408504", "disponible": True,
        }]},
    )

    titre: str = Field(min_length=2, max_length=200, description="Titre du livre (2 à 200 caractères).", examples=["Cosmos"])
    auteur: str = Field(min_length=2, max_length=200, description="Auteur du livre (2 à 200 caractères).", examples=["Carl Sagan"])
    annee: int = Field(description="Année de publication, entre 1450 et l'année en cours.", examples=[1980])
    categorie: Categorie = Field(description="Catégorie : roman, science, histoire, informatique ou autre.")
    isbn: str | None = Field(default=None, description="ISBN de 10 ou 13 chiffres (facultatif, unique).", examples=["9782070408504"])
    disponible: bool = Field(default=True, description="Vrai si le livre est disponible (valeur par défaut).")

    _annee = field_validator("annee")(verifier_annee)
    _isbn = field_validator("isbn")(normaliser_isbn)


class LivreUpdate(BaseModel):
    """Corps de PATCH : tous les champs sont facultatifs, seuls ceux envoyés sont modifiés."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
        json_schema_extra={"examples": [{"disponible": False}]},
    )

    titre: str | None = Field(default=None, min_length=2, max_length=200, description="Nouveau titre.")
    auteur: str | None = Field(default=None, min_length=2, max_length=200, description="Nouvel auteur.")
    annee: int | None = Field(default=None, description="Nouvelle année (1450 à l'année en cours).")
    categorie: Categorie | None = Field(default=None, description="Nouvelle catégorie.")
    isbn: str | None = Field(default=None, description="Nouvel ISBN (10 ou 13 chiffres) ; null pour l'effacer.")
    disponible: bool | None = Field(default=None, description="Nouvelle disponibilité.")

    _annee = field_validator("annee")(verifier_annee)
    _isbn = field_validator("isbn")(normaliser_isbn)

    @model_validator(mode="after")
    def refuser_null_explicite(self) -> "LivreUpdate":
        """Un champ obligatoire en base ne peut pas être remplacé par null."""
        for champ in CHAMPS_NON_NULLABLES:
            if champ in self.model_fields_set and getattr(self, champ) is None:
                raise ValueError(f"Le champ « {champ} » ne peut pas être null.")
        return self


class LivreRead(BaseModel):
    """Réponse : le livre tel qu'il est stocké, avec son identifiant généré par la base."""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Identifiant généré par la base.", examples=[1])
    titre: str
    auteur: str
    annee: int
    categorie: Categorie
    isbn: str | None = None
    disponible: bool


class Erreur(BaseModel):
    """Format des erreurs 404 et 409 produites par HTTPException."""
    detail: str = Field(examples=["Livre 42 introuvable."])
