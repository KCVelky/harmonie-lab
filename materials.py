"""Présélections transparentes : valeurs mesurées publiées ≠ panneau livré."""
MATERIALS = {
    "Bouleau CP — référence précédente (hypothèse isotrope)": dict(
        rho=650., Es=10., Eu=10., G=10/2.6, nu=.30,
        note="Valeurs de départ modifiables pour comparer rapidement les configurations.",
        source="Hypothèse de comparaison conservée, à remplacer par les propriétés du panneau acheté."),
    "Bouleau CP — WISA 4 mm / 3 plis (comparaison)": dict(
        rho=680., Es=16.471, Eu=1.029, G=.620, nu=.30,
        note="E de flexion et G de panneau publiés pour 4 mm ; nu=0,30 supposé. L'usage dans une plaque homogène équivalente reste approximatif. Non certifié pour 2 mm ; sélectionner 4 mm pour le produit de référence.",
        source="https://www.wisaplywood.com/siteassets/documents/dop/archive/upm007cpr-2016-11-11--2017-01-31-en.pdf"),
    "Bouleau CP — WISA 18 mm / 13 plis (comparaison)": dict(
        rho=680., Es=10.048, Eu=7.452, G=.620, nu=.30,
        note="E de flexion publiés pour 18 mm / 13 plis. G=0,620 GPa extrapolé du tableau, nu supposé. Ne décrit pas un CP mince de 2 mm.",
        source="https://www.wisaplywood.com/siteassets/documents/dop/archive/upm007cpr-2016-11-11--2017-01-31-en.pdf"),
    "Bouleau massif — exploration, à caractériser": dict(
        rho=650., Es=13., Eu=1.0, G=.95, nu=.43,
        note="Valeurs de travail arrondies, non attribuées à Sandra et non certifiées pour une essence, un débit ou une humidité précis. Les propriétés transversales doivent être caractérisées.",
        source="Jeu exploratoire entièrement modifiable, sans revendication de fiche matériau."),
    "Érable massif — exploration, à caractériser": dict(
        rho=700., Es=12., Eu=1.4, G=1.0, nu=.40,
        note="Érable cité pour le chevalet dans l'échange. Ici, option exploratoire pour la plaque ; toutes les constantes sont des hypothèses de travail à remplacer.",
        source="Jeu exploratoire entièrement modifiable, sans revendication de fiche matériau."),
    "Personnalisé": dict(rho=650.,Es=10.,Eu=10.,G=10/2.6,nu=.30,
        note="Entrer les valeurs de la fiche technique ou d'une identification expérimentale.",
        source="Données utilisateur.")
}
