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
   Pour l'étude actuelle, le bouton « Charger le scénario musée · 5 × 8 pi » applique directement la géométrie préliminaire des deux panneaux.
2. Régler le matériau, les dimensions et les appuis à gauche.
3. Éditer le tableau des cordes. Défiler horizontalement pour voir tous les paramètres.
4. Ouvrir « Modes et animations », sélectionner plaque ou ensemble, puis cliquer « Animer au ralenti ».
5. Dans « Accordage et cibles », choisir l’harmonique de chaque corde et configurer tous les électroaimants.
6. Charger une séquence CSV pour créer et écouter un plan de pilotage musical.
7. Dans « Réponse et son », créer l’écoute combinée de la table entière ou d’un point précis.
8. Ajuster au besoin une tension de corde ou l’épaisseur de la table, puis sauvegarder la configuration depuis la barre latérale.

### Étude Sandra : une corde longue

Dans l'onglet « Étude Sandra · une corde », charger le cas de référence : une corde vibrante de 10 m, fil de 0,762 mm, fondamentale accordée à 12 Hz, un aimant à 10 % de la corde, deux panneaux de 2,5 × 8 pi formant une table de 5 × 8 pi avec traverse centrale supposée. Le bouton de comparaison calcule la réponse de la table avec le chevalet à 10 %, puis à 22,5 % de la hauteur depuis le haut. Les harmoniques 5 et 7 sont examinés vers 60 et 84 Hz, aux résolutions 10, 12 et 14. Une comparaison de sensibilité aux fixations est disponible dans un volet séparé.

Le fichier T12 peut être déposé au format WAV ou dans l'archive ZIP fournie. Choisir le canal et l'hypothèse reliant la fréquence du courant à celle de la force avant d'analyser le spectre. Le fichier est transmis au serveur Streamlit et traité en mémoire pour la session ; il n'est pas inclus dans le dépôt. Le rapport pondéré par T12 est relatif et ne constitue ni une accélération étalonnée du bâtiment, ni un niveau sonore prédit dans la salle. Le point de contact corde–chevalet, le couplage, la force magnétique, la masse du chevalet, le matériau et les fixations restent des hypothèses modifiables.

### Page « Audibilité · étude pour Sandra »

La page distincte accessible par la navigation Streamlit déroule quatre étapes : projection de l'aimant et du contact sur les modes isolés, comparaison mécanique du chevalet à 10 % et 22,5 %, bandes de T12 avec gains de filtrage proposés, puis robustesse du classement aux hypothèses de fixation et d'amortissement. L'indice pondéré par T12 n'est affiché que si le calcul converge et si l'on suppose une force linéarisée à la fréquence de la commande avec conversion identique aux bandes retenues. Dans le cas quadratique idéalisé produisant une force à 2f, le logiciel n'en déduit pas de réponse pondérée à partir de la seule densité spectrale de T12.

Une section facultative accepte des mesures acoustiques **étalonnées** au même microphone, dans la même bande, aimant en marche et à l'arrêt, ainsi que la force harmonique crête du test. Elle calcule par soustraction énergétique le niveau attribuable à la source, puis une extrapolation linéaire pour une autre force. Si les mesures sont absentes ou si leur différence est trop faible, elle n'annonce aucun niveau sonore ni pourcentage d'audibilité. L'audio généré par l'application reste normalisé et ne constitue pas une mesure du volume réel.

Les boutons de calcul de réponse et de son génèrent un résultat pour les réglages courants. Un changement de paramètre peut effacer l'affichage du résultat : recliquer pour le recalculer.

### Page « Projection acoustique »

Cette page ajoute une projection **conditionnelle** de la réponse de la table vers un point d'écoute. Elle compare le chevalet à 10 % et 22,5 % depuis le haut, pour les 5e et 7e harmoniques d'une corde de 7,45 à 11,55 m. Le moteur structurel reste Rayleigh–Ritz ; seule une vérification indépendante de la corde tendue utilise des éléments finis 1D. La pression est calculée par intégrale de Rayleigh pour la face avant d'une table placée dans un écran rigide infini, sans salle, sans arrière ouvert et sans effet de boîte. Ce n'est **pas encore** un modèle éléments finis complet de l'instrument.

### Page « Instrument complet · étude prévisionnelle »

Cette page permet de régler jusqu'à 25 cordes, avec leur longueur, leur fondamentale isolée, l'harmonique ciblé, la position de l'aimant et sa force harmonique crête. L'aimant inactif ne supprime pas la corde de la structure ni du bilan de traction. Le jeu initial couvre 7,45 à 11,55 m et 12 à 9 Hz ; il est seulement illustratif. La traction totale est comparée à l'enveloppe de 550 kgf annoncée. Les 650–700 kgf évoqués ultérieurement ne sont pas considérés comme autorisés.

Le calcul couple toutes les cordes à la même table et compare le chevalet à 10 % et 22,5 % du haut. Il affiche les transferts acoustiques directs par corde, ainsi que leur variation entre deux résolutions mécaniques. Un fichier WAV de préécoute est créé par somme des pressions harmoniques, puis **normalisé** : son volume dans le lecteur ne représente pas le niveau réel du musée. Les dB SPL conditionnels ne s'affichent qu'après activation explicite et sont masqués lorsque la comparaison de résolutions échoue pour une corde active. Le WAV T12 peut être confronté aux bandes choisies sans transformer ses échantillons numériques en une force physique non étalonnée.

La quatrième étape de cette page explique les équations, les hypothèses et les mesures manquantes. Le modèle de table est Rayleigh–Ritz, pas un maillage éléments finis 2D. L'acoustique reste une intégrale de Rayleigh en écran rigide infini, sans dos de boîte ni réflexions. Cette page aide à sélectionner et documenter des essais ; elle n'atteste pas le niveau sonore réel.

Le résultat principal est un transfert en Pa RMS par newton de **force harmonique crête** à l'aimant. Une force nécessaire pour atteindre un niveau cible ne s'affiche qu'avec un bruit de fond saisi ; un niveau en dB SPL ne s'affiche qu'avec une force saisie. Dans les deux cas, le résultat dépend des hypothèses et ne prouve pas l'audibilité réelle dans le musée. La page vérifie la variation entre les ordres structurels 12 et 14 et n'affiche pas de force seuil ou de dB conditionnels pour une bande qui varie de plus de 10 %. Elle exporte les résultats mécano-acoustiques en CSV. Le calcul peut être exécuté localement avec la même interface Streamlit ; la version en ligne reste adaptée à cette étude légère.

Le fichier `exemple_fur_elise.csv` peut être chargé directement depuis l'interface. La mélodie est transposée une octave plus bas afin de rester proche des harmoniques disponibles avec les cordes par défaut.

## Inclus

- Plaque orthotrope, orientation du fil et trois fixations.
- Calcul Rayleigh–Ritz, masse de chevalet, modes propres et formes animées.
- 1 à 12 cordes, rigidité de flexion et paramètres individuels.
- Couplage mécanique réciproque, vibrations par sympathie.
- Deux points d'excitation par corde, gains, phases et entrefers.
- Géométrie 3D orientable, carte des nœuds, balayage fréquentiel.
- Scénario musée 5 × 8 pi, jonction centrale visible et traverse en bois ajoutée au calcul.
- Comparaison à une corde des positions de chevalet 10 % et 22,5 %, contrôle de convergence et lecture du WAV T12.
- Projection acoustique conditionnelle vers un point d'écoute, seuil de force associé à un bruit de fond saisi et contrôle éléments finis 1D de la corde.
- Tableau des fréquences réellement imposées et de leur réponse relative sur la table.
- Choix guidé des harmoniques, accordage inverse et recherche d'épaisseur.
- Lecture de séquences musicales CSV et export du pilotage des électroaimants en CSV ou JSON.
- Export JSON, CSV et WAV, sources et méthode intégrées.

**Lire METHODE.md** pour les hypothèses. Le son est indicatif et les propriétés des panneaux minces sont à identifier. Le collage central est supposé parfait ; la profondeur de traverse du scénario musée est une hypothèse. Les valeurs exploratoires bouleau/érable ne sont pas présentées comme les propositions originales de Sandra.

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

Fichiers principaux : app.py (interface), physics.py (mécanique), rayonnement.py (projection acoustique idéalisée), visuals.py (3D), materials.py (présélections et provenance).
