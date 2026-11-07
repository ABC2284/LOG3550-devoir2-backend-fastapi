// Frontend du catalogue relié à l'API FastAPI (fetch, async/await) : plus de localStorage.
(function () {
  'use strict';

  const API_URL = 'http://127.0.0.1:8000';
  const TAILLE_PAGE = 100; // limite maximale acceptée par l'API
  const ANNEE_MIN = 1450;
  const CATEGORIES = ['roman', 'science', 'histoire', 'informatique', 'autre'];
  const FILTRES_PAR_DEFAUT = { recherche: '', categorie: 'toutes', disponiblesSeulement: false };

  // État unique : la vue est toujours redessinée à partir de lui.
  const etat = {
    livres: [],
    filtres: { ...FILTRES_PAR_DEFAUT },
    tri: 'titre-asc',
    apiIndisponible: false
  };

  // ---------- Références DOM ----------
  const el = {
    recherche: document.getElementById('recherche'),
    categorie: document.getElementById('filtre-categorie'),
    dispo: document.getElementById('filtre-dispo'),
    tri: document.getElementById('tri'),
    effacerFiltres: document.getElementById('btn-effacer-filtres'),
    compteur: document.getElementById('compteur'),
    statut: document.getElementById('statut'),
    chargement: document.getElementById('etat-chargement'),
    erreurApi: document.getElementById('erreur-api'),
    texteErreurApi: document.getElementById('texte-erreur-api'),
    reessayer: document.getElementById('btn-reessayer'),
    liste: document.getElementById('liste-livres'),
    messageVide: document.getElementById('message-vide'),
    modele: document.getElementById('modele-livre'),
    formulaire: document.getElementById('formulaire-ajout'),
    ajouter: document.getElementById('btn-ajouter'),
    actualiser: document.getElementById('btn-actualiser')
  };

  // ---------- Utilitaires ----------
  // Minuscules et sans accents : « Éloge » devient « eloge ».
  function normaliser(texte) {
    return texte.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase().trim();
  }

  function majuscule(texte) {
    return texte.charAt(0).toUpperCase() + texte.slice(1);
  }

  // ---------- Communication avec l'API ----------
  // Transforme une réponse d'erreur FastAPI (404, 409 : texte ; 422 : liste) en message lisible.
  async function lireMessageErreur(reponse) {
    try {
      const corps = await reponse.json();
      if (typeof corps.detail === 'string') return corps.detail;
      if (Array.isArray(corps.detail)) {
        return corps.detail.map((e) => `${e.loc[e.loc.length - 1]} : ${e.msg}`).join(' ; ');
      }
    } catch (erreur) {
      // Réponse sans JSON : on retombe sur le code HTTP.
    }
    return `Erreur ${reponse.status} renvoyée par l'API.`;
  }

  // Appel générique : retourne le JSON (ou null pour 204) ou lève une Error au message clair.
  async function appelApi(chemin, options = {}) {
    let reponse;
    try {
      reponse = await fetch(`${API_URL}${chemin}`, {
        headers: { 'Content-Type': 'application/json' },
        ...options
      });
    } catch (erreur) {
      throw new Error("Impossible de joindre l'API. Vérifiez qu'elle est démarrée (uvicorn app.main:app --reload).");
    }
    if (!reponse.ok) throw new Error(await lireMessageErreur(reponse));
    return reponse.status === 204 ? null : reponse.json();
  }

  // L'API pagine (100 livres maximum par appel) : on lit toutes les pages.
  async function recupererTousLesLivres() {
    const tous = [];
    for (let debut = 0; ; debut += TAILLE_PAGE) {
      const page = await appelApi(`/livres?skip=${debut}&limit=${TAILLE_PAGE}`);
      tous.push(...page);
      if (page.length < TAILLE_PAGE) return tous;
    }
  }

  // ---------- Recherche, filtres et tri ----------
  function correspondAuxFiltres(livre, filtres) {
    const requete = normaliser(filtres.recherche);
    const texte = normaliser(`${livre.titre} ${livre.auteur}`);
    return texte.includes(requete)
      && (filtres.categorie === 'toutes' || livre.categorie === filtres.categorie)
      && (!filtres.disponiblesSeulement || livre.disponible);
  }

  function comparateur(tri) {
    const [champ, sens] = tri.split('-');
    const facteur = sens === 'asc' ? 1 : -1;
    if (champ === 'annee') return (a, b) => (a.annee - b.annee) * facteur;
    return (a, b) => a.titre.localeCompare(b.titre, 'fr', { sensitivity: 'base' }) * facteur;
  }

  function livresAffiches() {
    return etat.livres
      .filter((livre) => correspondAuxFiltres(livre, etat.filtres))
      .sort(comparateur(etat.tri));
  }

  function filtresActifs() {
    const { recherche, categorie, disponiblesSeulement } = etat.filtres;
    return recherche.trim() !== '' || categorie !== 'toutes' || disponiblesSeulement;
  }

  // ---------- Affichage ----------
  function creerCarte(livre) {
    const carte = el.modele.content.firstElementChild.cloneNode(true);
    carte.dataset.id = livre.id;
    carte.dataset.categorie = livre.categorie;
    carte.querySelector('.carte__titre').textContent = livre.titre;
    carte.querySelector('.carte__auteur').textContent = livre.auteur;
    carte.querySelector('.carte__details').textContent = `${majuscule(livre.categorie)} · ${livre.annee}`;

    const etiquette = carte.querySelector('.etiquette');
    etiquette.textContent = livre.disponible ? 'Disponible' : 'Emprunté';
    etiquette.classList.add(livre.disponible ? 'etiquette--dispo' : 'etiquette--emprunte');

    const bouton = carte.querySelector('button');
    bouton.dataset.action = 'supprimer';
    bouton.setAttribute('aria-label', `Supprimer « ${livre.titre} »`);
    return carte;
  }

  function afficherCompteur(nombre) {
    if (etat.apiIndisponible) {
      el.compteur.textContent = '';
      return;
    }
    const total = etat.livres.length;
    const mot = nombre > 1 ? 'résultats' : 'résultat';
    el.compteur.textContent = `${nombre} ${mot} sur ${total} livre${total > 1 ? 's' : ''}`;
  }

  function afficher() {
    const livres = livresAffiches();
    el.liste.replaceChildren(...livres.map(creerCarte));
    el.messageVide.hidden = livres.length > 0 || etat.apiIndisponible;
    afficherCompteur(livres.length);
    el.effacerFiltres.disabled = !filtresActifs();
  }

  function annoncer(message) {
    el.statut.textContent = message;
  }

  function afficherChargement(actif) {
    el.chargement.hidden = !actif;
    el.actualiser.disabled = actif;
  }

  function afficherErreurApi(message) {
    el.texteErreurApi.textContent = message;
    el.erreurApi.hidden = false;
  }

  function masquerErreurApi() {
    el.erreurApi.hidden = true;
    el.texteErreurApi.textContent = '';
  }

  // ---------- Chargement initial et actualisation ----------
  async function chargerLivres() {
    afficherChargement(true);
    masquerErreurApi();
    annoncer('');
    try {
      etat.livres = await recupererTousLesLivres();
      etat.apiIndisponible = false;
    } catch (erreur) {
      etat.livres = [];
      etat.apiIndisponible = true;
      afficherErreurApi(erreur.message);
    } finally {
      afficherChargement(false);
      afficher();
    }
  }

  // ---------- Filtres : lecture des contrôles ----------
  function lireFiltres() {
    etat.filtres = {
      recherche: el.recherche.value,
      categorie: el.categorie.value,
      disponiblesSeulement: el.dispo.checked
    };
    afficher();
  }

  function effacerFiltres() {
    etat.filtres = { ...FILTRES_PAR_DEFAUT };
    el.recherche.value = '';
    el.categorie.value = 'toutes';
    el.dispo.checked = false;
    afficher();
    el.recherche.focus();
  }

  // ---------- Suppression ----------
  async function supprimerLivre(id) {
    const livre = etat.livres.find((l) => l.id === id);
    if (!livre) return;
    if (!window.confirm(`Supprimer « ${livre.titre} » du catalogue ?`)) return;
    masquerErreurApi();
    try {
      await appelApi(`/livres/${id}`, { method: 'DELETE' });
      etat.livres = etat.livres.filter((l) => l.id !== id);
      afficher();
      annoncer(`« ${livre.titre} » a été supprimé.`);
    } catch (erreur) {
      afficherErreurApi(erreur.message);
    }
  }

  function surClicListe(evenement) {
    const bouton = evenement.target.closest('button[data-action="supprimer"]');
    if (!bouton) return;
    supprimerLivre(Number(bouton.closest('.carte').dataset.id));
  }

  // ---------- Formulaire : validation côté client ----------
  function lireFormulaire() {
    const donnees = new FormData(el.formulaire);
    return {
      titre: donnees.get('titre').trim(),
      auteur: donnees.get('auteur').trim(),
      annee: donnees.get('annee').trim(),
      categorie: donnees.get('categorie'),
      disponible: donnees.get('disponible') !== null
    };
  }

  // Retourne un objet { champ: message } ; vide si tout est valide.
  function validerLivre(valeurs) {
    const erreurs = {};
    const anneeCourante = new Date().getFullYear();
    const annee = Number(valeurs.annee);

    if (valeurs.titre.length < 2) erreurs.titre = 'Le titre est obligatoire (2 caractères minimum).';
    if (valeurs.auteur.length < 2) erreurs.auteur = "L'auteur est obligatoire (2 caractères minimum).";
    if (valeurs.annee === '' || !Number.isInteger(annee) || annee < ANNEE_MIN || annee > anneeCourante) {
      erreurs.annee = `L'année doit être un nombre entier entre ${ANNEE_MIN} et ${anneeCourante}.`;
    }
    if (!CATEGORIES.includes(valeurs.categorie)) erreurs.categorie = 'Choisissez une catégorie.';
    return erreurs;
  }

  function afficherErreurs(erreurs) {
    ['titre', 'auteur', 'annee', 'categorie'].forEach((champ) => {
      const entree = document.getElementById(champ);
      const zone = document.getElementById(`erreur-${champ}`);
      zone.textContent = erreurs[champ] || '';
      if (erreurs[champ]) entree.setAttribute('aria-invalid', 'true');
      else entree.removeAttribute('aria-invalid');
    });
    const premier = Object.keys(erreurs)[0];
    if (premier) document.getElementById(premier).focus();
  }

  // ---------- Ajout via l'API ----------
  async function surEnvoiFormulaire(evenement) {
    evenement.preventDefault();
    const valeurs = lireFormulaire();
    const erreurs = validerLivre(valeurs);
    afficherErreurs(erreurs);
    if (Object.keys(erreurs).length > 0) return;

    masquerErreurApi();
    el.ajouter.disabled = true; // évite un double envoi pendant la requête
    try {
      const cree = await appelApi('/livres', {
        method: 'POST',
        body: JSON.stringify({ ...valeurs, annee: Number(valeurs.annee) })
      });
      etat.livres.push(cree);
      el.formulaire.reset();
      afficher();
      annoncer(`« ${cree.titre} » a été ajouté au catalogue.`);
    } catch (erreur) {
      afficherErreurApi(erreur.message);
    } finally {
      el.ajouter.disabled = false;
    }
  }

  // ---------- Initialisation ----------
  function brancherEvenements() {
    el.recherche.addEventListener('input', lireFiltres);
    el.categorie.addEventListener('change', lireFiltres);
    el.dispo.addEventListener('change', lireFiltres);
    el.tri.addEventListener('change', () => { etat.tri = el.tri.value; afficher(); });
    el.effacerFiltres.addEventListener('click', effacerFiltres);
    el.liste.addEventListener('click', surClicListe);
    el.formulaire.addEventListener('submit', surEnvoiFormulaire);
    el.actualiser.addEventListener('click', chargerLivres);
    el.reessayer.addEventListener('click', chargerLivres);
  }

  function initialiser() {
    document.getElementById('annee').max = new Date().getFullYear();
    document.getElementById('annee').min = ANNEE_MIN;
    brancherEvenements();
    chargerLivres();
  }

  initialiser();
})();
