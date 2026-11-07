"""Points d'accès CRUD pour les livres."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, or_, select

from app.database import get_session
from app.models import Categorie, Livre
from app.schemas import Erreur, LivreCreate, LivreRead, LivreUpdate

router = APIRouter(prefix="/livres", tags=["Livres"])

SessionDep = Annotated[Session, Depends(get_session)]

REPONSE_404 = {"model": Erreur, "description": "Livre introuvable."}
REPONSE_409 = {"model": Erreur, "description": "Un autre livre possède déjà cet ISBN."}


def trouver_livre(session: Session, livre_id: int) -> Livre:
    """Retourne le livre ou lève une erreur 404."""
    livre = session.get(Livre, livre_id)
    if livre is None:
        raise HTTPException(status_code=404, detail=f"Livre {livre_id} introuvable.")
    return livre


def enregistrer(session: Session, livre: Livre) -> Livre:
    """Enregistre le livre ; l'index unique de la base signale un ISBN en double (409)."""
    session.add(livre)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Un livre avec cet ISBN existe déjà.")
    session.refresh(livre)
    return livre


@router.get(
    "",
    response_model=list[LivreRead],
    summary="Lister les livres",
    description="Retourne les livres, triés par identifiant. Filtres combinables : `q` (titre ou auteur), "
                "`categorie`, `disponible`. Pagination avec `skip` et `limit` (maximum 100).",
)
def lister_livres(
    session: SessionDep,
    q: Annotated[str | None, Query(description="Texte cherché dans le titre ou l'auteur.")] = None,
    categorie: Annotated[Categorie | None, Query(description="Filtrer par catégorie.")] = None,
    disponible: Annotated[bool | None, Query(description="Filtrer par disponibilité.")] = None,
    skip: Annotated[int, Query(ge=0, description="Nombre de livres à sauter.")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Nombre maximal de livres (1 à 100).")] = 20,
):
    requete = select(Livre)
    if q:
        motif = f"%{q}%"
        requete = requete.where(or_(col(Livre.titre).ilike(motif), col(Livre.auteur).ilike(motif)))
    if categorie is not None:
        requete = requete.where(Livre.categorie == categorie)
    if disponible is not None:
        requete = requete.where(Livre.disponible == disponible)
    return session.exec(requete.order_by(Livre.id).offset(skip).limit(limit)).all()


@router.get(
    "/{livre_id}",
    response_model=LivreRead,
    summary="Lire un livre",
    description="Retourne le livre correspondant à l'identifiant, ou 404 s'il n'existe pas.",
    responses={404: REPONSE_404},
)
def lire_livre(livre_id: int, session: SessionDep):
    return trouver_livre(session, livre_id)


@router.post(
    "",
    response_model=LivreRead,
    status_code=201,
    summary="Créer un livre",
    description="Crée un livre. Répond 201 avec l'en-tête `Location` pointant vers le nouveau livre. "
                "L'identifiant est généré par la base ; 409 si l'ISBN existe déjà.",
    responses={409: REPONSE_409},
)
def creer_livre(donnees: LivreCreate, session: SessionDep, request: Request, response: Response):
    livre = enregistrer(session, Livre(**donnees.model_dump()))
    response.headers["Location"] = str(request.url_for("lire_livre", livre_id=livre.id))
    return livre


@router.put(
    "/{livre_id}",
    response_model=LivreRead,
    summary="Remplacer un livre",
    description="Remplacement complet : tous les champs sont réécrits (un champ omis reprend sa valeur par défaut).",
    responses={404: REPONSE_404, 409: REPONSE_409},
)
def remplacer_livre(livre_id: int, donnees: LivreCreate, session: SessionDep):
    livre = trouver_livre(session, livre_id)
    for champ, valeur in donnees.model_dump().items():
        setattr(livre, champ, valeur)
    return enregistrer(session, livre)


@router.patch(
    "/{livre_id}",
    response_model=LivreRead,
    summary="Modifier partiellement un livre",
    description="Modifie seulement les champs envoyés ; les autres restent inchangés.",
    responses={404: REPONSE_404, 409: REPONSE_409},
)
def modifier_livre(livre_id: int, donnees: LivreUpdate, session: SessionDep):
    livre = trouver_livre(session, livre_id)
    for champ, valeur in donnees.model_dump(exclude_unset=True).items():
        setattr(livre, champ, valeur)
    return enregistrer(session, livre)


@router.delete(
    "/{livre_id}",
    status_code=204,
    summary="Supprimer un livre",
    description="Supprime le livre. Répond 204 sans contenu, ou 404 s'il n'existe pas.",
    responses={404: REPONSE_404},
)
def supprimer_livre(livre_id: int, session: SessionDep):
    livre = trouver_livre(session, livre_id)
    session.delete(livre)
    session.commit()
