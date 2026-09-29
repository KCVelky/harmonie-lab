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

Le rayonnement acoustique de la plaque, les annulations entre lobes, l'effet dipolaire de l'arrière ouvert, la cavité, le local et le haut-parleur d'écoute ne sont pas calculés. Aucun niveau en dB SPL n'est revendiqué. Le timbre réel pourrait être très différent.

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
