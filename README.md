# Harmonie Lab — prototype de Sandra

Application Python locale, interface en français, pour explorer les vibrations d'une table d'harmonie reliée à plusieurs cordes métalliques et électroaimants.

## Installation Windows (sans droits administrateur si Python est déjà installé)

Utiliser Python **3.11 ou 3.12**. Extraire tout le ZIP dans un dossier accessible, puis ouvrir un terminal dans ce dossier.

    py -3 -m venv .venv
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    .venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --browser.gatherUsageStats false

Après cette première installation, un double-clic sur **lancer_windows.bat** relance l'application.

Si la commande py n'existe pas mais python fonctionne, remplacer py -3 par python.
Aucune activation PowerShell de l'environnement n'est nécessaire.

## macOS / Linux

    python3 -m venv .venv
    .venv/bin/python -m pip install -r requirements.txt
    bash lancer_mac_linux.sh

L'interface s'ouvre à **http://127.0.0.1:8501**. Garder le terminal ouvert. Ctrl+C arrête le serveur. L'application et ses calculs tournent sur votre ordinateur ; aucun compte n'est demandé. Internet est nécessaire pour installer les bibliothèques. Ensuite, les vues et animations fonctionnent hors ligne, Plotly étant inclus localement. Les liens de documentation sont externes uniquement si vous les ouvrez.

## Prise en main

1. Commencer avec la référence 610 × 305 × 2 mm, cinq cordes et deux aimants par corde.
2. Régler le matériau, les dimensions et les appuis à gauche.
3. Éditer le tableau des cordes. Défiler horizontalement pour voir tous les paramètres.
4. Ouvrir « Modes et animations », sélectionner plaque ou ensemble, puis cliquer « Animer au ralenti ».
5. Dans « Accordage et cibles », choisir l’harmonique de chaque corde et configurer tous les électroaimants.
6. Charger une séquence CSV pour créer et écouter un plan de pilotage musical.
7. Dans « Réponse et son », créer l’écoute combinée de la table entière ou d’un point précis.
8. Ajuster au besoin une tension de corde ou l’épaisseur de la table, puis sauvegarder la configuration depuis la barre latérale.

Les boutons de calcul de réponse et de son génèrent un résultat pour les réglages courants. Un changement de paramètre peut effacer l'affichage du résultat : recliquer pour le recalculer.

Le fichier `exemple_fur_elise.csv` peut être chargé directement depuis l'interface. La mélodie est transposée une octave plus bas afin de rester proche des harmoniques disponibles avec les cordes par défaut.

## Inclus

- Plaque orthotrope, orientation du fil et trois fixations.
- Calcul Rayleigh–Ritz, masse de chevalet, modes propres et formes animées.
- 1 à 12 cordes, rigidité de flexion et paramètres individuels.
- Couplage mécanique réciproque, vibrations par sympathie.
- Deux points d'excitation par corde, gains, phases et entrefers.
- Géométrie 3D orientable, carte des nœuds, balayage fréquentiel.
- Choix guidé des harmoniques, accordage inverse et recherche d'épaisseur.
- Lecture de séquences musicales CSV et export du pilotage des électroaimants en CSV ou JSON.
- Export JSON, CSV et WAV, sources et méthode intégrées.

**Lire METHODE.md** pour les hypothèses. Le son est indicatif et les propriétés du panneau de 2 mm sont à identifier. Les valeurs exploratoires bouleau/érable ne sont pas présentées comme les propositions originales de Sandra.

## Repères vérifiés

Avec la référence isotrope E=10 GPa, rho=650 kg/m³, nu=0,30, plaque 610 × 305 × 2 mm et **masse de chevalet nulle** :
- appuis simples : premier mode ≈ 50,106 Hz ;
- quatre bords encastrés : premier mode ≈ 99,823 Hz (Ritz, ordre 6).

Le réglage par défaut ajoute un chevalet de 10 g : la fréquence affichée de plaque est donc légèrement différente. Le premier mode couplé peut être dominé par une corde : il ne faut pas le confondre avec le fondamental de la plaque.

## Tests facultatifs

    python -m pip install pytest
    python -m pytest -q

Adapter python au chemin de votre environnement virtuel. Les tests couvrent le calcul physique et des interactions de l'interface via Streamlit AppTest. Ils ne remplacent pas une campagne expérimentale.

Bibliothèques : NumPy, SciPy, pandas, Plotly, Streamlit. Aucune bibliothèque audio système, carte graphique spécialisée ou licence de calcul n'est requise. Un navigateur avec WebGL est nécessaire pour la 3D.

Fichiers principaux : app.py (interface), physics.py (mécanique), visuals.py (3D), materials.py (présélections et provenance).
