"""Tests de l'API : base SQLite en mémoire, séparée de la vraie base."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.database import get_session
from app.main import app

LIVRE = {"titre": "Cosmos", "auteur": "Carl Sagan", "annee": 1980, "categorie": "science"}


@pytest.fixture
def client():
    """Un client de test avec une base vide et neuve pour chaque test."""
    moteur = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(moteur)

    def session_test():
        with Session(moteur) as session:
            yield session

    app.dependency_overrides[get_session] = session_test
    yield TestClient(app)
    app.dependency_overrides.clear()
    moteur.dispose()


def creer(client, **changements):
    """Crée un livre via l'API et retourne la réponse."""
    return client.post("/livres", json={**LIVRE, **changements})


def test_sante(client):
    reponse = client.get("/sante")
    assert reponse.status_code == 200
    assert reponse.json() == {"statut": "ok"}


def test_creation_retourne_201_location_et_id_genere(client):
    reponse = creer(client, isbn="9782070408504")
    assert reponse.status_code == 201
    livre = reponse.json()
    assert livre["id"] >= 1
    assert livre["disponible"] is True  # valeur par défaut
    assert reponse.headers["location"].endswith(f"/livres/{livre['id']}")


def test_lecture_d_un_livre(client):
    livre_id = creer(client).json()["id"]
    reponse = client.get(f"/livres/{livre_id}")
    assert reponse.status_code == 200
    assert reponse.json()["titre"] == "Cosmos"


def test_lecture_inexistante_retourne_404(client):
    reponse = client.get("/livres/999")
    assert reponse.status_code == 404
    assert reponse.json() == {"detail": "Livre 999 introuvable."}


def test_liste_filtree_et_pagination(client):
    creer(client)
    creer(client, titre="Clean Code", auteur="Robert C. Martin", annee=2008, categorie="informatique")
    creer(client, titre="Le Petit Prince", auteur="Antoine de Saint-Exupéry", annee=1943,
          categorie="roman", disponible=False)

    assert len(client.get("/livres").json()) == 3
    assert [l["titre"] for l in client.get("/livres", params={"q": "sagan"}).json()] == ["Cosmos"]
    assert [l["titre"] for l in client.get("/livres", params={"categorie": "informatique"}).json()] == ["Clean Code"]
    assert [l["titre"] for l in client.get("/livres", params={"disponible": False}).json()] == ["Le Petit Prince"]
    assert len(client.get("/livres", params={"skip": 1, "limit": 1}).json()) == 1


def test_limite_superieure_a_100_retourne_422(client):
    assert client.get("/livres", params={"limit": 101}).status_code == 422


def test_remplacement_complet_put(client):
    livre_id = creer(client, isbn="9782070408504").json()["id"]
    nouveau = {"titre": "Contact", "auteur": "Carl Sagan", "annee": 1985, "categorie": "roman"}
    reponse = client.put(f"/livres/{livre_id}", json=nouveau)
    assert reponse.status_code == 200
    assert reponse.json()["titre"] == "Contact"
    assert reponse.json()["isbn"] is None  # PUT remplace tout : l'ISBN omis est effacé


def test_modification_partielle_patch(client):
    livre_id = creer(client).json()["id"]
    reponse = client.patch(f"/livres/{livre_id}", json={"disponible": False})
    assert reponse.status_code == 200
    assert reponse.json()["disponible"] is False
    assert reponse.json()["titre"] == "Cosmos"  # le reste est inchangé


def test_suppression_retourne_204_puis_404(client):
    livre_id = creer(client).json()["id"]
    assert client.delete(f"/livres/{livre_id}").status_code == 204
    assert client.get(f"/livres/{livre_id}").status_code == 404
    assert client.delete(f"/livres/{livre_id}").status_code == 404


def test_titre_trop_court_retourne_422(client):
    reponse = creer(client, titre="A")
    assert reponse.status_code == 422
    assert reponse.json()["detail"][0]["loc"] == ["body", "titre"]


def test_annee_future_retourne_422(client):
    assert creer(client, annee=3000).status_code == 422


def test_isbn_invalide_retourne_422(client):
    assert creer(client, isbn="12345").status_code == 422


def test_id_fourni_par_le_client_est_refuse(client):
    assert creer(client, id=5).status_code == 422


def test_categorie_inconnue_retourne_422(client):
    assert creer(client, categorie="cuisine").status_code == 422


def test_isbn_en_double_retourne_409(client):
    assert creer(client, isbn="9782070408504").status_code == 201
    reponse = creer(client, titre="Autre livre", isbn="9782070408504")
    assert reponse.status_code == 409
    assert "ISBN" in reponse.json()["detail"]


def test_patch_vers_un_isbn_existant_retourne_409(client):
    creer(client, isbn="9782070408504")
    second = creer(client, titre="Autre livre", isbn="1234567890").json()["id"]
    assert client.patch(f"/livres/{second}", json={"isbn": "9782070408504"}).status_code == 409
