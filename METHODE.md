### Ce que le modèle représente

La plaque rectangulaire est décrite par la théorie de Kirchhoff–Love, en petites déformations, avec propriétés orthotropes homogénéisées. Les cordes ont une tension imposée et une rigidité de flexion. Les ancrages sont fixes et indépendants de la plaque. Chaque corde peut être excitée en deux points.

La traction du châssis n'est pas appliquée en compression à la plaque. Le chevalet ajoute une masse répartie sur une ligne transversale, mais sa rigidité propre n'est pas calculée. Les vis et le cadre périphérique sont visuels ; leur souplesse individuelle est remplacée par la condition de bord choisie. Une traverse centrale optionnelle peut en revanche ajouter sa masse et sa rigidité au modèle.

Le chevalet est un contact **intermédiaire** sur chaque corde : sa position βL est comptée depuis l'ancrage inférieur, et L désigne la distance entre les deux ancrages. Si les 800–1200 mm de Sandra correspondent au segment chevalet–ancrage supérieur, il faut entrer une autre longueur totale. Le modèle ne prétend pas trancher cette ambiguïté de construction.

### Plaque : formulation énergétique

On écrit w(s,u,t)=Σ Bᵢ(s,u)qᵢ(t). La courbure est κ=[w,ss ; w,uu ; 2w,su].

En axes matériau, D11=E1 h³/[12(1−ν12ν21)], D22=E2 h³/[12(1−ν12ν21)], D12=ν12 E2 h³/[12(1−ν12ν21)] et D66=G12 h³/12, avec ν21=ν12 E2/E1. La matrice est tournée suivant l'angle du fil choisi.

Kᵢⱼ=∫ κᵢᵀ D κⱼ dA ; Mᵢⱼ=∫ ρh BᵢBⱼ dA. La masse du chevalet ajoute (m_c/W)∫ Bᵢ(s_c,u)Bⱼ(s_c,u)du. Il s'agit d'une masse distribuée suivant la déformée locale, pas d'une barre infiniment rigide.

Les intégrales utilisent une quadrature de Gauss. La résolution de K v=ω² M v donne des modes normalisés à vᵀMv=1. La fréquence vaut f=ω/(2π). Le solveur utilisé est [scipy.linalg.eigh](https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.eigh.html).

- **Appuis simples** : base sin(mπs/H)sin(nπu/W). Le déplacement est nul aux quatre bords. Pour une plaque orthotrope alignée sans masse ajoutée, la solution fréquentielle est analytique dans cette base.
- **Rotation élastique** : même base, avec énergie de bord ½∫kθ(∂w/∂n)²dl. kθ est exprimé en N, équivalent à N·m par radian et par mètre. kθ=0 redonne l'appui simple. Les grandes raideurs exigent une base plus riche.
- **Encastrement** : base de Ritz formée de polynômes de Legendre multipliés par ξ²(1−ξ)² sur chaque axe. Déplacement et pente sont nuls exactement aux bords. Les fréquences approchées convergent en enrichissant la base.

Un joint flexible en translation n'est pas représenté. On ne peut donc pas affirmer que tout montage par vis/joint aura automatiquement sa fréquence entre les deux modèles limites. Les modes élevés, les matériaux fortement anisotropes et les angles de fil obliques demandent une vérification de convergence.

### Jonction centrale et traverse en bois

Le scénario « Table du musée » représente deux panneaux coplanaires dont le collage central est supposé parfait. La continuité de déplacement et de pente est donc celle d'une plaque homogénéisée ; une fissure, un glissement ou une couche de colle souple ne sont pas résolus.

La pièce de bois placée sous la jonction est une poutre verticale d'Euler–Bernoulli solidaire de la plaque. Pour une section de largeur b et de profondeur d, elle ajoute une masse linéique ρbd et une rigidité de flexion Ebd³/12. L'énergie et la masse sont intégrées le long de la ligne u=u_j. Ce modèle permet d'étudier l'effet préliminaire d'une traverse, mais pas les contraintes locales dans la colle ni les assemblages au cadre.

### Cordes, tension et couplage

Pour une corde isolée, A=πd²/4, I=πd⁴/64, μ=ρA, k_n=nπ/L :

ω_n²=(T k_n² + EI k_n⁴)/μ.

La masse modale vaut μL/2. La forme sin(nπx/L) correspond à des extrémités à déplacement nul et moment nul ; la rigidité rotationnelle réelle des ancrages est omise.

La tension inverse pour un partiel n est T=μ(2πf)²/k_n²−EI k_n². Une valeur négative est rejetée. Il s'agit de l'accordage **isolé**, avant perturbation par le chevalet.

Au contact j, l'énergie ajoutée est ½k_c[y_j(βL)−w(s_c,u_j)]². Elle produit une matrice symétrique positive et assure un échange mécanique réciproque entre corde et plaque. k_c est un paramètre d'identification, pas une constante connue du prototype. Il représente un contact linéarisé autour d'un équilibre préchargé ; il ne résout ni glissement ni décollement.

Les positions des aimants modifient les forces modales par sin(nπp). Elles ne modifient pas les fréquences propres dans ce modèle, car l'attraction statique et la raideur magnétique sont omises. Les cordes non excitées restent couplées et peuvent vibrer par sympathie.

### Réponse forcée et amortissement

Dans la base des modes couplés :

q_r(ω)=F_r/[ω_r²−ω²+2iζ_rω_rω].

Le taux ζ_r est pondéré par les fractions de masse modale de la plaque et de chaque corde. Il s'agit d'un amortissement modal diagonal supposé, pas d'un calcul de toutes les pertes aux contacts.

Les deux aimants d'une corde ont une position, un entrefer, un gain et une phase relative. La force de référence est une **force harmonique crête étalonnée**, supposée à g_ref=3 mm. Le facteur (g_ref/g)² est un réglage exploratoire local : ni saturation, ni géométrie magnétique réelle, ni commande de courant ne sont calculées. La loi F∝I² peut créer du continu et du 2f : le champ « excitation » désigne la fréquence de force.

Le balayage applique une fréquence commune aux aimants actifs ; les phases sont conservées. L'écoute entretenue utilise les fréquences individuelles de chaque corde.

Le tableau « Quelles fréquences la table joue-t-elle ? » évalue séparément chaque corde à sa fréquence imposée. Les catégories forte, moyenne et faible sont définies relativement à la plus grande accélération de la configuration : au-dessus de −6 dB, entre −18 et −6 dB, puis sous −18 dB. Elles servent à repérer un déséquilibre interne et ne constituent pas un niveau sonore absolu.

### Son : ce que l'on entend

Le WAV est une sonification de l'accélération normale en un point choisi de la plaque. Le régime entretenu superpose les réponses forcées. Le régime impulsionnel applique une impulsion équivalente de 1 ms aux points d'excitation puis laisse décroître les modes ; les phases de commande sont ignorées dans ce régime.

Le signal est normalisé à chaque génération, avec fondus de 25 ms, et exporté à 44,1 kHz / PCM 16 bits. Comparer deux volumes ne permet donc pas de comparer leur rendement. Les modes dépassant 0,45 fois la fréquence d'échantillonnage sont exclus de l'impulsion.

Dans l'interface principale, le rayonnement acoustique de la plaque, les annulations entre lobes, l'effet dipolaire de l'arrière ouvert, la cavité, le local et le haut-parleur d'écoute ne sont pas calculés. Aucun niveau en dB SPL n'est revendiqué pour cet audio normalisé. Le timbre réel pourrait être très différent. Une page distincte donne une projection acoustique sous hypothèse d'écran rigide infini, décrite ci-dessous.

### Projection acoustique conditionnelle

La page « Projection acoustique » reprend la réponse mécanique couplée de `physics.py` pour une corde, avec une force harmonique crête normalisée à 1 N au premier aimant, un second aimant désactivé et un entrefer de référence de 3 mm. Les fréquences de force sont les 5e et 7e fréquences de la corde **isolée** ; la réponse contient bien le couplage corde–table. La masse du chevalet (5 kg par défaut sur cette page), le module et la masse volumique isotropes du panneau, la traverse, le contact et les appuis sont des **hypothèses modifiables**, non des données identifiées du prototype. La table est supposée verticale, son centre à une hauteur réglable, la face avant orientée vers la distance positive du point d'écoute.

Pour les phasors définis avec une dépendance temporelle exp(iωt), la pression complexe de la face avant dans un **écran rigide infini** est obtenue par l'intégrale de Rayleigh :

`p(r) = -ρ_air ω²/(2π) ∫_S w(x) exp(-ikR)/R dS`, avec `R=|r-x|` et `k=ω/c`.

Ici `w(x)` est l'amplitude complexe crête du déplacement normal. Les valeurs utilisées sont ρ_air=1,20 kg/m³ et c=343 m/s ; l'intégration est faite par quadrature de Gauss 48 × 48. Le transfert affiché est `|p|/(√2 F_crête)` en Pa RMS/N crête. Pour une force crête saisie `F`, le niveau conditionnel est `20 log10[(|p| F /√2)/(20 µPa)]` dB SPL. Le calcul inverse de force pour une cible `L_cible` est `F_requise = 20 µPa × 10^(L_cible/20) / transfert`. Ces relations sont linéaires seulement tant que la mécanique, l'électroaimant et le contact peuvent être linéarisés autour de leur état de fonctionnement.

L'intégrale conserve les phases de chaque zone de la table et peut produire des annulations spatiales. Elle ne représente pas le dos ouvert, une éventuelle cavité, les réflexions et modes de la salle, la diffraction du cadre, ni le chargement de retour de l'air sur la structure. Le résultat ne constitue donc ni une borne garantie ni une prédiction de niveau dans le musée. La force magnétique dynamique sur le fil de 0,762 mm est inconnue. Les valeurs en dB n'apparaissent qu'après saisie explicite d'une force ; l'utilisateur doit distinguer hypothèse et mesure. Le bruit de fond n'est pas présumé connu : il doit être saisi dans la même bande avant un calcul de force requise. Une marge au-dessus du fond reste une cible choisie, pas une loi d'audibilité.

La stabilité numérique de la projection est vérifiée en comparant les ordres de Rayleigh–Ritz 12 et 14, avec une variation relative maximale de 10 % pour chacun des deux emplacements de chevalet. Une bande qui dépasse ce seuil n'alimente pas les résultats conditionnels de force seuil ou de dB. Cette vérification ne couvre ni les erreurs de modèle ni les incertitudes des données. Une vérification séparée de la corde sous tension utilise des éléments finis 1D linéaires à masse cohérente, avec 48 et 96 éléments, comparés à `f_n=n/(2L)√(T/µ)`. La flexion du fil est omise dans ce seul contrôle 1D mais reste incluse dans le modèle couplé. La plaque n'est pas encore discrétisée par éléments finis.

### Instrument complet : résolution haute fréquence

La page « Instrument complet » utilise, pour les **appuis simples et le panneau isotrope seulement**, une base exacte pour la plaque rectangulaire idéale : `φ_nm(s,u)=sin(nπs/H)sin(mπu/W)`. Dans cette base, la masse nue vaut `ρhHW/4` et la raideur nue `D(HW/4)[(nπ/H)²+(mπ/W)²]²`, avec `D=Eh³/[12(1−ν²)]`. Les contributions de la traverse, de la masse linéique du chevalet et des 25 contacts sont calculées à partir des mêmes énergies que dans `physics.py`. Les matrices assemblées à petit ordre coïncident numériquement avec celles du modèle existant.

La réponse à une force de fréquence imposée est obtenue en résolvant `[(1+iη_p)K_p+(1+iη_s)K_s+K_c−ω²M]q=F`, avec des facteurs de perte structurels `η_p=2ζ_p` et `η_s=2ζ_s` pour la plaque et les cordes ; la traverse reçoit par hypothèse le même facteur de perte que la plaque. Le contact `K_c` reste élastique sans perte. Ce choix n'est pas identique à l'amortissement modal de la page à une corde et empêche d'attribuer toute différence entre ces deux pages aux seuls appuis. Les termes de traverse, chevalet et contact ont un faible rang ; la formule de Woodbury réduit le coût de résolution sans modifier la matrice dynamique correspondante. Un test compare cette solution à une résolution directe de la matrice complète.

La pression de chaque aimant est calculée par la même intégrale acoustique de Rayleigh. Les raies de fréquences différentes sont additionnées en **énergie moyenne** pour le niveau collectif. À fréquence strictement identique, la page distingue une somme complexe à phase commandée commune et une somme énergétique non synchronisée. Elle vérifie sur plusieurs ordres la variation relative `(max p − min p)/max p` de chaque raie et, séparément, du niveau collectif. Une raie proche d'une annulation acoustique peut avoir une forte variation *relative* tout en contribuant très peu au niveau total ; son classement est alors écarté sans masquer automatiquement le résultat collectif. Le seuil de 10 % est un critère numérique de travail, non un intervalle de confiance physique.

Par défaut, les ordres 34, 38 et 42 donnent sur le jeu illustratif de 25 cordes une variation du niveau collectif calculé d'environ 1,9 % pour le chevalet à 10 % et 0,4 % pour le chevalet à 22,5 %. Ces nombres ne valent que pour ce jeu, ces propriétés et ce modèle. La jonction, le dos et la salle ne sont toujours pas résolus ; la force dynamique réelle des aimants reste inconnue. Pour les **bords encastrés**, la page conserve le solveur modal d'ordre inférieur et signale son caractère exploratoire.

### Page d'audibilité et mesure acoustique

La page dédiée compare la vibration spatiale quadratique de la plaque pour les mêmes force, corde et table, en déplaçant seulement le chevalet entre 10 % et 22,5 % depuis le haut. Les projections |sin(nπp)| de l'aimant et du contact ne concernent que les modes d'une corde isolée. La comparaison mécanique vérifie sa convergence entre trois résolutions ; les variantes de structure la vérifient entre deux résolutions. Une variante non convergée n'autorise aucun verdict.

Dans une bande de ±1 Hz centrée sur la fréquence de commande, l'énergie numérique de T12 est estimée par la somme des densités spectrales de puissance multipliée par le pas fréquentiel. Un gain de filtre G en dB multiplie cette énergie par 10^(G/10). L'indice pondéré compare la racine de la moyenne des carrés des accélérations de plaque, pondérée par ces énergies. Son interprétation suppose une conversion commande-force identique aux bandes, un filtrage approximativement plat dans chaque bande et un transfert linéarisé à la même fréquence. Le facteur de force inconnu commun s'annule dans le **rapport** entre les deux positions, mais pas dans un niveau absolu. Pour une force quadratique à 2f, le spectre de force dépend des produits et mélanges du signal temporel ; la seule énergie de T12 à f/2 est insuffisante à cette fin.

La section acoustique ne s'active qu'avec des niveaux dB SPL RMS mesurés au même microphone dans une même bande fréquentielle. Sous l'hypothèse de fond comparable et de contributions énergétiques indépendantes, le niveau de la source est Ls=10 log10(10^(Lon/10)−10^(Loff/10)). Une différence marche/arrêt inférieure à 3 dB est traitée comme non concluante, seuil pratique de cette interface et non loi d'audibilité. Pour un même montage et une réponse linéaire, une force de référence Fr et une force prévue Fp donnent Lp=Ls+20 log10(Fp/Fr). Le contraste Lp−Loff est un indicateur local et fréquentiel ; la page ne le convertit ni en perception garantie ni en probabilité. Si le niveau change fortement avec la force, l'hypothèse de linéarité doit être testée sur l'électroaimant réel.

### Géométrie et hypothèses de départ

Références reprises : châssis 1524 × 305 × 305 mm ; plaque libre 610 × 305 × **2 mm** ; cinq cordes de diamètre 0,762 mm, longueurs réparties de 800 à 1200 mm ; deux aimants par corde ; chevalet à 122 mm du bord inférieur ; zone technique de 610 mm.

Hypothèses ajoutées et modifiables : plaque à 420 mm du sol, 16 N par corde, masse de chevalet de 10 g, β=0,28, contact k_c=500 N/m, angles de 3°, aimants à 0,12L et 0,20L avec jeux de 3 mm et force de référence 0,01 N. Les positions intermédiaires de longueur ne sont pas des valeurs mesurées fournies par Sandra.

La largeur libre 305 mm plus les appuis périphériques ne tient pas dans un châssis extérieur de 305 mm. Le diagnostic conserve cette contradiction pour qu'elle soit corrigée explicitement. Les pièces visibles ont des sections schématiques ; ce n'est pas un plan de fabrication.

Le scénario musée utilise une surface verticale de 1524 × 2438,4 × 3,175 mm, assemblée à partir de deux panneaux de 762 × 2438,4 mm. L'élévation enregistrée est 15 m. Faute d'autres dimensions, la traverse centrale est supposée carrée, 38,1 × 38,1 mm, avec ρ=500 kg/m³ et E=10 GPa. La plaque est prise en appuis simples, le dos est ouvert et le matériau reprend provisoirement l'hypothèse isotrope historique. Ces choix doivent faire l'objet d'une étude de sensibilité avant verdict.

### Matériaux et sources

Consultation des sources : 11 septembre 2026.

1. **Référence historique du projet** : E=10 GPa, ρ=650 kg/m³, ν=0,30, modèle isotrope. Valeurs hypothétiques conservées pour comparer aux calculs précédents ; elles ne certifient pas un CP aviation de 2 mm.
2. **UPM WISA, déclaration UPM007CPR, 2016/2017, page 2** : le CP bouleau 4 mm / 3 plis a des modules de flexion parallèles et perpendiculaires de 16,471 et 1,029 GPa. Le 18 mm / 13 plis : 10,048 et 7,452 GPa. La masse volumique moyenne est 680 kg/m³. Le G de panneau de 0,620 GPa est indiqué dans les premières colonnes ; son usage pour 18 mm est une extrapolation explicitée. ν=0,30 est supposé. Ces valeurs de flexion sont utilisées dans une homogénéisation approximative ; changer l'épaisseur ne reconstitue pas automatiquement un nouvel empilement de plis. [Déclaration fabricant](https://www.wisaplywood.com/siteassets/documents/dop/archive/upm007cpr-2016-11-11--2017-01-31-en.pdf).
3. **UPM WISA, masse volumique** : 680±50 kg/m³ pour le CP bouleau. Cette variabilité justifie un paramètre éditable. [Masses et dimensions](https://www.wisaplywood.com/specifying-wisa/sizes-thicknesses-and-weights/).
4. **M&R Spring, Music Wire ASTM A228** : E=30 000 000 psi et ρ=0,284 lb/in³, soit environ 206,843 GPa et 7861 kg/m³. Ce sont les valeurs initiales des cordes. La résistance admissible et le facteur de sécurité ne sont pas déduits du seul module E. [Table fournisseur](https://www.mrspring.com/products/custom-springs/).
5. **Bouleau et érable massifs exploratoires** : constantes de travail arrondies, sans certification ni attribution à Sandra. Elles doivent être remplacées par une fiche correspondant à l'essence, au débit et à l'humidité. La liste exacte des matériaux proposés par Sandra n'a pas été retrouvée ; elle n'est pas reconstituée artificiellement.

### Limites et validation utile

La flèche statique est obtenue par K_plaque q=F, avec F_j=2T_j sin(α_j/2). À flèche comparable à l'épaisseur, la théorie linéaire non précontrainte n'est plus suffisante. Les anciennes estimations par poutre équivalente (plusieurs mm) ne sont pas utilisées comme données de validation.

Le logiciel ne dimensionne ni la résistance du cadre, ni les vis, ni le flambement, ni la rupture des cordes. Il calcule toutefois la traction totale et les contraintes axiales pour permettre un contrôle indépendant.

Pour identifier le prototype : mesurer les fréquences et décroissances de la plaque nue ; ajouter le chevalet ; mesurer une corde isolée ; identifier le contact avec une corde couplée ; étalonner force/commande/entrefer ; enfin comparer le système à cinq cordes. Adapter E1, E2, G12, la fixation et les amortissements à ces mesures.
