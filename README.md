# LOG3550 – Devoir 2 : Backend FastAPI

**Auteur :** Julmice Carl Verlet · ISTEAH · LOG3550 Développement web

**Dépôt Git :*https://github.com/ABC2284/LOG3550-devoir2-backend-fastapi.git*

## Description
API REST FastAPI qui gère les livres du catalogue du devoir 1 : validation Pydantic, stockage SQLite avec SQLModel, 16 tests pytest. Le frontend du devoir 1 (dossier `frontend/`) lit, ajoute et supprime les livres par l'API avec `fetch` au lieu du `localStorage`.

## Arborescence
```
devoir2/
  app/
    main.py            (application, CORS, routeurs, démarrage)
    database.py        (moteur SQLite, session, livres de départ)
    models.py          (table Livre, Enum Categorie)
    schemas.py         (LivreCreate, LivreUpdate, LivreRead)
    routers/livres.py  (points d'accès CRUD)
  tests/test_livres.py (16 tests, base en mémoire)
  frontend/            (frontend du devoir 1, relié à l'API)
  captures/            (captures numérotées)
  requirements.txt  .gitignore  README.md
```

## Installation, lancement et tests
```bash
python -m venv venv
venv\Scripts\activate            # Windows  (Linux/macOS : source venv/bin/activate)
pip install -r requirements.txt

uvicorn app.main:app --reload    # API sur http://127.0.0.1:8000 · documentation sur /docs
pytest -v                        # lance les tests (base en mémoire, séparée)
```
Pour le frontend, dans un second terminal, à la racine du projet :
```bash
python -m http.server 5500 --directory frontend
```
Puis ouvrir http://localhost:5500. Le CORS n'autorise que `http://localhost:5500` et `http://127.0.0.1:5500` (modifiable avec la variable d'environnement `ORIGINES_AUTORISEES`). La base `bibliotheque.db` est créée au premier démarrage avec 10 livres de départ ; elle est ignorée par Git.

## Points d'accès
| Méthode | Chemin | Rôle | Codes |
|---|---|---|---|
| GET | `/livres` | Liste (filtres `q`, `categorie`, `disponible` ; `skip`, `limit` ≤ 100) | 200, 422 |
| GET | `/livres/{id}` | Lire un livre | 200, 404 |
| POST | `/livres` | Créer (en-tête `Location`) | 201, 409, 422 |
| PUT | `/livres/{id}` | Remplacement complet | 200, 404, 409, 422 |
| PATCH | `/livres/{id}` | Modification partielle | 200, 404, 409, 422 |
| DELETE | `/livres/{id}` | Supprimer | 204, 404 |
| GET | `/sante` | `{"statut": "ok"}` | 200 |

## Choix de conception
- **Séparation modèle / schémas** : `models.py` décrit la table, `schemas.py` décrit ce qui entre et sort de l'API. Le client ne peut jamais fournir d'`id` (`extra="forbid"` → 422).
- **ISBN unique garanti par la base** : index unique sur la colonne ; le code attrape `IntegrityError` et répond 409. Aucun contrôle préalable qui pourrait être contourné par deux requêtes simultanées.
- **Session par dépendance** (`Depends(get_session)`) : une session par requête, fermée à la fin.
- **Tests isolés** : la dépendance de session est remplacée par une base SQLite en mémoire, recréée pour chaque test ; la vraie base n'est jamais touchée.
- **Frontend** : `fetch` avec `async`/`await`, état de chargement, message d'erreur avec bouton « Réessayer » si l'API est arrêtée. La recherche sans accents reste faite côté client sur la liste reçue (l'API pagine par 100 ; le frontend lit toutes les pages).
- **Sécurité** : aucune clé ni mot de passe, `.gitignore` exclut `venv/`, `*.db` et les caches, CORS sans astérisque.

## Questions d'explication

### 1. Rôle de FastAPI, d'Uvicorn et de Pydantic ; pourquoi séparer modèle et schémas
- **FastAPI** est le framework : il associe les URL aux fonctions Python et génère la documentation `/docs`.
- **Uvicorn** est le serveur : il reçoit les requêtes HTTP et les transmet à FastAPI.
- **Pydantic** valide les données reçues et renvoyées à partir des types et des règles déclarés.
- Le **modèle** décrit la table (avec `id` et contraintes de base), les **schémas** décrivent le contrat de l'API.
- Les séparer évite d'exposer ou d'accepter des champs internes (comme l'`id`) et permet de changer l'un sans casser l'autre.

### 2. Format d'une erreur 422
- FastAPI répond `{"detail": [ ... ]}` : une liste, avec une entrée par règle non respectée.
- `loc` indique l'endroit de l'erreur, par exemple `["body", "titre"]` (corps de la requête, champ `titre`).
- `msg` est le message lisible et `type` le code de la règle (`string_too_short`, `enum`, `extra_forbidden`…).
- `input` rappelle la valeur reçue et `ctx` donne les détails (par exemple `min_length`).
- Toutes les erreurs de la requête sont renvoyées en une fois, ce qui permet de tout corriger d'un coup.

### 3. Différence entre PUT et PATCH ; idempotence
- **PUT** remplace la ressource en entier : tous les champs sont envoyés, un champ omis revient à sa valeur par défaut.
- **PATCH** modifie seulement les champs envoyés ; les autres restent inchangés.
- Une opération est **idempotente** si la répéter donne le même état final qu'une seule fois.
- PUT (même contenu écrit à chaque fois) et DELETE (le livre est absent après le premier appel) sont idempotents.
- POST ne l'est pas : chaque appel crée une nouvelle ressource avec un nouvel `id`.

## Difficultés rencontrées
- Refuser un `id` envoyé par le client : résolu avec `extra="forbid"` dans les schémas d'entrée.
- Garantir l'unicité de l'ISBN même si plusieurs ISBN sont absents : index unique (les valeurs `NULL` multiples sont permises par SQLite) et traduction de `IntegrityError` en 409.
- Empêcher qu'un PATCH mette `null` dans un champ obligatoire : validateur `model_validator` dans `LivreUpdate`.
- Tester sans toucher à la vraie base : base SQLite en mémoire avec `StaticPool` et remplacement de la dépendance `get_session`.

## Captures
1. `captures/1-swagger-docs.png` — page `/docs` avec tous les points d'accès _(à ajouter)_
2. `captures/2a-erreur-422.png` et `captures/2b-erreur-422.png` — deux réponses 422 _(à ajouter)_
3. `captures/3-pytest-v.png` — `pytest -v` au vert _(à ajouter)_
4. `captures/4-catalogue-alimente-par-api.png` — catalogue alimenté par l'API
5. `captures/5-onglet-reseau-post.png` — requête POST dans l'onglet Réseau _(à ajouter)_

## Sources et outils d'assistance utilisés
- Assistant IA : **Claude (Anthropic)** a servi à générer une première version du code, des tests et du README ; le code a ensuite été relu et doit être compris par l'auteur.
- Documentation : FastAPI (fastapi.tiangolo.com), SQLModel (sqlmodel.tiangolo.com), Pydantic, MDN Web Docs (`fetch`, CORS).
