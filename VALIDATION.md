# Vérifications — 11 septembre 2026

18 tests automatisés réussis dans l'environnement Python 3.12 utilisé pour la préparation.

- Plaque simplement appuyée : spectre comparé à la formule analytique.
- Plaque encastrée : fondamental 99,823 Hz et respect des déplacements/pentes de bord.
- Variation linéaire des fréquences avec l'épaisseur pour une plaque nue.
- Invariance de rotation d'un matériau isotrope.
- Limite d'appui simple et effet positif des ressorts de rotation.
- Spectre découplé, résidus propres et normalisation en masse.
- Inversion de tension et recherche d'épaisseur.
- Linéarité de la déflexion statique.
- Nœuds d'excitation et correction d'entrefer.
- WAV fini, signal silencieux sans excitation.
- Rejet des paramètres invalides.
- Cohérence des formes modales sur une grille 2D et des trames d'animation.
- Interface Streamlit AppTest : matériau, encastrement, nombre de cordes,
  choix des modes, accordage, épaisseur inverse, remise à zéro,
  réponse fréquentielle, génération audio, convergence et diagnostic d'entrée invalide.

Valeurs de référence sans masse de chevalet, E=10 GPa, rho=650 kg/m³,
nu=0,30, 610 × 305 × 2 mm :
appuis simples 50,1062856 Hz ; encastrement Ritz ordre 6 : 99,8233581 Hz.

Limite des contrôles : AppTest exécute l'interface et les interactions côté Python.
La lecture sur une carte son et le rendu WebGL dans le navigateur du PC utilisateur
n'ont pas été contrôlés sur ce matériel. Aucune validation expérimentale du prototype.
