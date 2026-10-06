# Harmonie Lab — passation pour reprendre le projet sur un autre PC

Mise à jour : 6 octobre 2026. Ce document donne le contexte nécessaire à un nouveau chat et les étapes pour récupérer le code. Il ne remplace pas la lecture du code, de `README.md` et de `METHODE.md` avant une modification scientifique.

## 1. Où se trouvent le site et le code ?

- Application publique : <https://harmonie-lab.streamlit.app/>
- Page « Audibilité · étude pour Sandra » : <https://harmonie-lab.streamlit.app/Audibilite>
- Dépôt du code : <https://github.com/KCVelky/harmonie-lab>
- Branche de travail : `main`.
- Point de référence vérifié lors de cette passation : commit `91577f5` (`Add audibility evidence page for Sandra study`). Le dépôt peut avoir avancé depuis ; consulter son historique avant de travailler.

Le site permet d'utiliser l'application depuis n'importe quel PC. Pour modifier le logiciel, il faut récupérer le dépôt GitHub. Le fait de retrouver une conversation ChatGPT sur un second PC ne copie pas les fichiers locaux.

## 2. Récupérer le projet sur le PC de la maison

### Solution conseillée : Git

1. Installer Git et Python **3.11 ou 3.12** sur le nouveau PC, si nécessaire.
2. Ouvrir PowerShell dans le dossier où conserver le projet, puis exécuter :

   ```powershell
   git clone https://github.com/KCVelky/harmonie-lab.git
   cd harmonie-lab
   py -3 -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   .venv\Scripts\python.exe -m streamlit run app.py
   ```

3. Ouvrir l'adresse locale affichée par Streamlit, en général `http://localhost:8501`.
4. Dans Codex/ChatGPT sur ce PC, créer ou ouvrir un projet local pointant vers le dossier `harmonie-lab`, puis donner ce fichier Markdown au nouveau chat. Demander au chat de lire aussi `README.md` et `METHODE.md`.

Si `py` n'existe pas, utiliser `python` pour créer l'environnement. Par la suite, `lancer_windows.bat` permet de relancer l'application avec l'environnement installé.

Pour récupérer les changements publiés après le clonage : `git pull` dans le dossier du projet. Pour partager les changements faits à la maison avec l'autre PC, il faut les enregistrer puis les envoyer sur GitHub ; éviter de travailler simultanément sur les deux copies sans synchronisation. Si Git est trop compliqué, le bouton **Code → Download ZIP** de GitHub fournit une copie, mais elle est moins pratique à mettre à jour.

### Fichiers qui ne suivront pas automatiquement

Le WAV/ZIP **T12** envoyé par Sandra n'est pas publié dans le dépôt. Lors de cette passation, ces fichiers d'étude étaient aussi uniquement sur le PC initial : `ETUDE_PRELIMINAIRE_MUSEE.md`, `etude_musee.py`, `generer_figures_musee.py` et `figures_courriel_musee/`. Les transférer séparément, par un moyen approprié et avec les autorisations nécessaires, si le travail à domicile en dépend. Ne pas publier par défaut l'enregistrement ou des données de Sandra dans le dépôt public. Le dossier `.venv` ne se transfère pas : il se recrée avec `requirements.txt`.

## 3. Contexte du projet

Sandra conçoit une installation au musée visant à rendre perceptibles les vibrations d'un bâtiment. Le chemin envisagé est : captation du bâtiment (notamment T12) → traitement par canal dans MAX/MSP → électroaimants → longues cordes → chevalet → table d'harmonie → son dans la salle. Une variation de l'activité du bâtiment ou de la fréquentation pourrait modifier le résultat, mais **cet effet sur la captation et sur le son n'a pas été démontré**.

Le point central est l'audibilité. Les fondamentales envisagées pour les longues cordes, de l'ordre de **9 à 12 Hz**, sont infrasonores ; leurs harmoniques peuvent se trouver dans la plage audible. Exemple idéal pour une corde à 12 Hz : 5e harmonique vers 60 Hz, 7e vers 84 Hz. Il faut à la fois de l'énergie disponible dans le signal de commande, une force réellement produite par l'électroaimant, une excitation efficace de la corde, une transmission au chevalet et une réponse/rayonnement suffisants de la table. La simple proximité entre fréquence de corde et mode de table ne garantit pas un son audible.

La proposition de Sandra est physiquement cohérente comme stratégie **à tester**, pas comme garantie : sélectionner/renforcer certaines bandes de T12 pour chaque corde, placer les aimants hors des nœuds des harmoniques visées, ajuster l'accordage et comparer la réponse de la table. Les essais grandeur réelle devront confirmer le résultat.

### Contraintes et informations communiquées

- Géométrie provisoire de la table : environ **5 × 8 pieds**, verticale, formée de deux panneaux de contreplaqué de **2,5 × 8 pieds × 1/8 pouce**, joints au centre et supportés par du bois d'environ **1,5 pouce**. La table serait placée vers **15 m de hauteur**, à proximité du chevalet. Le type exact de jonction, les fixations et la cavité éventuelle ne sont pas entièrement définis.
- Cordes envisagées : **8 à 12 m**, fil à piano **12.5 GA, diamètre 0,762 mm** ; fondamentales approximatives 9–12 Hz. Sandra a annoncé aux ingénieurs une enveloppe d'environ **550 kgf (5,4 kN) pour 25 cordes**. Le cordier pèse environ **47 kg** ; la masse exacte du chevalet n'est pas fournie.
- T12 : enregistrement exploratoire par accéléromètre **Dytran 3100D24T**, conditionneur CCLD et enregistreur Sound Devices 744T. L'accéléromètre n'a pas été réétalonné récemment ; chantier, travaux et conditions non contrôlées. Une nouvelle campagne est prévue. Un pic spectral ne prouve donc pas une composante permanente du bâtiment ni un effet des visiteurs.

Ne pas confondre trois positions : l'aimant est repéré en fraction de la **longueur de corde** ; le contact corde–chevalet a aussi une position sur la corde ; la comparaison **10 % / 22,5 %** déplace le chevalet sur la **hauteur de la table à partir du haut**. Dans la page d'audibilité, seul ce dernier emplacement change entre les deux colonnes comparées.

## 4. État du modèle et de l'application

L'interface principale est dans `app.py`. Elle contient la géométrie, les matériaux et appuis, les cordes, les modes, l'accordage, la réponse mécanique, la sonification et un lecteur de séquences CSV. La page séparée `pages/1_Audibilite.py` présente une étude ciblée à **une corde** : (1) corde et table, (2) analyse du signal T12, (3) robustesse aux hypothèses, (4) preuve acoustique conditionnelle. Les calculs sont notamment dans `physics.py`, `etude_sandra.py`, `audibilite.py` et `analyse_t12.py`.

Le scénario d'audibilité par défaut prend une corde de **10 m**, **0,762 mm**, accordée à **12 Hz** isolée, un aimant à **10 %** de la corde et un contact corde–chevalet à **5 %** de la corde. Les positions de chevalet sur la table sont **10 % et 22,5 % depuis le haut**. Le calcul examine les 5e et 7e harmoniques, avec un contrôle de convergence aux ordres 10, 12 et 14. Les paramètres mécaniques non mesurés sont explicitement modifiables. Ne pas considérer le cas par défaut comme une description certifiée de l'installation future.

La plaque est modélisée en petites déformations par une approximation de Kirchhoff–Love et une méthode Rayleigh–Ritz. Les cordes sont linéarisées et couplées à la plaque par une raideur de contact supposée. La jonction centrale est supposée parfaitement collée ; une traverse idéalisée ajoute masse et rigidité. Les fixations, le matériau réel, l'amortissement, le contact et la force magnétique restent incertains. Le modèle mécanique **ne calcule pas encore le rayonnement acoustique, la salle ou le niveau sonore réel des visiteurs**. Voir `METHODE.md` pour les équations et limites.

L'indicateur « Indice mécanique T12 · 10 % / 22,5 % » est un **rapport de vibration calculée** entre les deux positions, pondéré par l'énergie numérique de T12 dans les bandes choisies. Par exemple, `0,60 ×` signifierait que, sous les hypothèses saisies, la première position donne 60 % de l'indice mécanique de la seconde. Ce n'est ni un rendement acoustique, ni une probabilité d'audibilité. Son interprétation suppose notamment une conversion commande → force identique dans les bandes et une force à la même fréquence que la commande. Si la force est essentiellement quadratique et apparaît à `2f`, cette pondération ne suffit pas.

La section « Preuve acoustique » ne déduit des dB SPL **que si l'utilisateur saisit des mesures étalonnées** avec aimant en marche et à l'arrêt, au même microphone et dans la même bande, ainsi qu'une force de référence. Les valeurs préremplies dans les champs sont des exemples de saisie, **pas des mesures de Sandra**. Le WAV synthétisé par l'application est normalisé ; son volume d'écoute n'est pas celui de l'instrument réel. Sans mesure acoustique, ne donner ni dB SPL prédit ni « pourcentage de confiance » d'audibilité.

Les principaux tests sont `test_physics.py`, `test_sandra.py`, `test_audibilite.py` et `test_ui.py`. Exécution après installation :

```powershell
.venv\Scripts\python.exe -m pip install pytest
.venv\Scripts\python.exe -m pytest -q
```

## 5. Objectif des prochaines discussions

Conserver une démarche en trois temps :

1. **Ce qui est déjà soutenu** : cohérence théorique de l'excitation d'harmoniques audibles et comparaison mécanique numérique, avec convergence et sensibilité aux hypothèses.
2. **Ce qui reste à estimer** : force réelle de l'électroaimant, comportement de la table construite, rayonnement acoustique et niveau reçu dans la salle. Un modèle vibroacoustique plus fidèle peut être envisagé, mais il exige des propriétés et conditions aux limites mieux identifiées. Il ne doit pas produire des dB « crédibles » à partir de paramètres inventés.
3. **Ce qui devra être validé** : essai avec le matériel réel, à une corde puis à l'échelle pertinente, et mesures micro/ambiance aux positions d'écoute représentatives.

Pour avancer sans confondre hypothèses et faits, demander au besoin à Sandra les éléments qu'elle ne peut pas simplement régler dans l'interface : référence et caractéristiques des électroaimants et de leur alimentation/commande, matériau exact des panneaux, détails de la jonction et des fixations, masses et géométries réelles du chevalet et du cordier, caractéristiques de l'accéléromètre/chaîne d'acquisition, et données d'une nouvelle captation contrôlée. Les positions d'aimant et certains réglages sont justement des variables de conception ; ne pas les présenter comme des données fixes à obtenir avant tout calcul.

## 6. Consigne à donner au nouveau chat

> Je reprends Harmonie Lab sur un autre PC. Lis entièrement `PASSATION_NOUVEAU_PC.md`, puis `README.md` et `METHODE.md`. Inspecte l'état réel du dépôt avant de proposer ou de modifier quoi que ce soit. Distingue systématiquement les données communiquées par Sandra, les hypothèses du modèle, les résultats mécaniques et les niveaux acoustiques mesurés. Je veux continuer l'étude de l'audibilité sans promettre un niveau sonore non validé. Demande-moi la tâche précise que je souhaite faire ensuite si je ne l'ai pas donnée.
