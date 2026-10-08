"""Projection vibroacoustique conditionnelle du scénario musée."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from rayonnement import (acoustic_level, evaluate_projection,
                         force_for_target_level, string_fem_tension_modes,
                         summarize_projection)


st.set_page_config(page_title='Projection acoustique · Harmonie Lab',
                   page_icon='🔊', layout='wide')
st.title('Projection acoustique')
st.write('De la vibration calculée de la table à une pression sonore **conditionnelle** au point d’écoute.')
st.info('Cette étude utilise la structure modale actuelle (Rayleigh–Ritz) et une intégrale acoustique de Rayleigh. Elle n’est pas un calcul éléments finis complet de la table, de la boîte et de la salle. Les niveaux affichés avec une force saisie ne sont pas des mesures de l’instrument.')


@st.cache_data(show_spinner=False, max_entries=8)
def calculate(length, fundamental, magnet, contact, coupling, damping,
              center_height, front_distance, lateral_offset, ear_height,
              bridge_mass, modulus, density, boundary, support_enabled):
    return evaluate_projection(
        length, fundamental, magnet / 100, contact / 100, coupling,
        damping, center_height,
        (front_distance, lateral_offset, ear_height),
        bridge_mass_kg=bridge_mass, plate_modulus_gpa=modulus,
        plate_density_kg_m3=density, boundary=boundary,
        support_enabled=support_enabled)


with st.sidebar:
    st.header('Scénario de calcul')
    st.caption('Une corde, table verticale 5 × 8 pi, deux panneaux de 1/8 po. Les propriétés et la jonction restent hypothétiques.')
    length = st.number_input('Longueur vibrante (m)', 7.45, 11.55, 10.0, .05)
    fundamental = st.number_input('Fondamentale isolée visée (Hz)', 9.0, 15.0,
                                  12.0, .25)
    magnet = st.number_input('Aimant sur la corde (% de L)', 1.0, 99.0, 10.0, .5)
    contact = st.number_input('Contact corde–chevalet (% de L)', 1.0, 30.0,
                              5.0, .5)
    st.divider()
    st.subheader('Point d’écoute supposé')
    center_height = st.number_input('Hauteur du centre de la table (m)',
                                    2.0, 30.0, 15.0, .5)
    front_distance = st.number_input('Distance devant la table (m)',
                                     .5, 30.0, 5.0, .5)
    lateral_offset = st.number_input('Décalage latéral (m)', -20.0, 20.0,
                                     0.0, .5)
    ear_height = st.number_input('Hauteur de l’oreille (m)', .5, 3.0, 1.6, .1)
    with st.expander('Hypothèses mécaniques'):
        bridge_mass = st.number_input('Masse totale du chevalet (kg) · hypothèse',
                                      0.0, 100.0, 5.0, .5)
        modulus = st.number_input('Module isotrope du panneau (GPa) · hypothèse',
                                  1.0, 30.0, 10.0, .5)
        density = st.number_input('Masse volumique du panneau (kg/m³) · hypothèse',
                                  300.0, 1200.0, 650.0, 25.0)
        boundary = st.selectbox('Bords idéalisés',
                                ['Appuis simples', 'Encastrement'])
        support_enabled = st.checkbox('Traverse centrale solidaire', value=True)
        coupling = st.number_input('Raideur de contact (N/m)', 1.0, 10000.0,
                                   500.0, 50.0)
        damping = st.number_input('Amortissement modal table ζ', .001, .10,
                                  .012, .001, format='%.3f')


st.subheader('1 · Ce que le modèle peut comparer')
st.write('Les valeurs ci-dessous sont calculées pour **1 N crête de force harmonique sur un aimant**, à la fréquence du 5ᵉ ou du 7ᵉ harmonique isolé. Elles expriment un transfert, pas la force disponible avec l’électroaimant réel.')
if st.button('Calculer 10 % et 22,5 %', type='primary'):
    try:
        with st.spinner('Calcul mécanique et intégration acoustique…'):
            rows, wire = calculate(length, fundamental, magnet, contact,
                                   coupling, damping, center_height,
                                   front_distance, lateral_offset, ear_height,
                                   bridge_mass, modulus, density, boundary,
                                   support_enabled)
        st.session_state.projection = (rows, wire)
        st.session_state.projection_key = (length, fundamental, magnet, contact,
                                           coupling, damping, center_height,
                                           front_distance, lateral_offset,
                                           ear_height, bridge_mass, modulus,
                                           density, boundary, support_enabled)
    except ValueError as exc:
        st.error(str(exc))

key = (length, fundamental, magnet, contact, coupling, damping,
       center_height, front_distance, lateral_offset, ear_height,
       bridge_mass, modulus, density, boundary, support_enabled)
saved = (st.session_state.get('projection')
         if st.session_state.get('projection_key') == key else None)

if saved is None:
    st.caption('Lance le calcul. Changer un paramètre efface le résultat précédent pour éviter de lire un ancien scénario comme s’il était à jour.')
else:
    rows, wire = saved
    summary = summarize_projection(rows)
    metric_columns = st.columns(3)
    metric_columns[0].metric('Tension de la corde étudiée', f'{wire.T:.1f} N')
    metric_columns[1].metric('25 cordes identiques · illustration',
                             f'{25 * wire.T / 9.80665:.0f} kgf')
    metric_columns[2].metric('Position du chevalet',
                             '10 % ou 22,5 % du haut')
    st.caption('La charge de 25 cordes identiques n’est pas la charge du projet : il faut sommer séparément les 25 longueurs et accords réels. L’enveloppe de 550 kgf annoncée aux ingénieurs n’est pas relevée automatiquement à 650–700 kgf.')

    table_rows = []
    for result in summary:
        table_rows.append({
            'Harmonique': result['harmonic'],
            'Fréquence de force (Hz)': result['frequency_hz'],
            '10 % · Pa RMS/N crête': result['pressure_0.1'],
            '22,5 % · Pa RMS/N crête': result['pressure_0.225'],
            '10 % / 22,5 %': result['ratio_first_over_second'],
            'Variation 10 %': result['convergence_0.1'],
            'Variation 22,5 %': result['convergence_0.225'],
            'Résolution': 'suffisante' if result['stable'] else 'à affiner',
        })
    frame = pd.DataFrame(table_rows)
    st.dataframe(frame, hide_index=True, width='stretch', column_config={
        'Fréquence de force (Hz)': st.column_config.NumberColumn(format='%.2f'),
        '10 % · Pa RMS/N crête': st.column_config.NumberColumn(format='%.3g'),
        '22,5 % · Pa RMS/N crête': st.column_config.NumberColumn(format='%.3g'),
        '10 % / 22,5 %': st.column_config.NumberColumn(format='%.2f'),
        'Variation 10 %': st.column_config.NumberColumn(format='%.1%'),
        'Variation 22,5 %': st.column_config.NumberColumn(format='%.1%'),
    })
    plot = go.Figure()
    for name, field, color in (
        ('Chevalet à 10 %', 'pressure_0.1', '#5da5fa'),
        ('Chevalet à 22,5 %', 'pressure_0.225', '#f5a451'),
    ):
        plot.add_bar(name=name, x=[f'{r["frequency_hz"]:.1f} Hz' for r in summary],
                     y=[r[field] for r in summary], marker_color=color)
    plot.update_layout(barmode='group', height=380,
                       yaxis_title='Pression RMS par N crête (Pa/N)',
                       xaxis_title='Fréquence de la force',
                       legend_title_text='Position depuis le haut',
                       margin=dict(l=15, r=15, t=20, b=15))
    st.plotly_chart(plot, width='stretch')
    if all(result['stable'] for result in summary):
        st.success('Dans les deux bandes, le transfert calculé varie de moins de 10 % entre les ordres 12 et 14. Cela vérifie cette résolution numérique, pas les hypothèses physiques.')
    else:
        st.warning('Au moins une bande varie de plus de 10 % entre les ordres 12 et 14. Les calculs de seuil et de niveau conditionnel excluent cette bande : son classement reste indéterminé.')

    st.subheader('2 · Que faudrait-il pour dépasser un bruit de fond ?')
    st.write('Le niveau de bruit doit concerner **la même bande fréquentielle** et une position d’écoute représentative. Le calcul ci-dessous est une analyse de seuil dans un champ acoustique idéalisé, pas une preuve que l’aimant peut fournir la force demandée.')
    if st.checkbox('Étudier un bruit de fond mesuré ou supposé'):
        noise_kind = st.radio('Origine du niveau saisi',
                              ['Hypothèse de travail', 'Mesure dans la salle'],
                              horizontal=True)
        ambient = st.number_input('Bruit de fond dans la bande (dB SPL RMS)',
                                  0.0, 110.0, 40.0, 1.0)
        margin = st.number_input('Écart cible au-dessus du fond (dB)',
                                 0.0, 30.0, 6.0, 1.0)
        st.caption('L’écart cible est un choix d’étude, pas un seuil universel de perception. Si les deux bandes ont des bruits de fond différents, les évaluer séparément.')
        threshold_rows = []
        for result in summary:
            if not result['stable']:
                continue
            for label, field in (('10 %', 'pressure_0.1'),
                                 ('22,5 %', 'pressure_0.225')):
                required = force_for_target_level(result[field], ambient + margin)
                threshold_rows.append({
                    'Fréquence (Hz)': result['frequency_hz'],
                    'Chevalet': label,
                    'Force crête requise (N)': required,
                    'Validité numérique': ('suffisante' if result['stable']
                                           else 'à affiner'),
                })
        if threshold_rows:
            st.dataframe(pd.DataFrame(threshold_rows), hide_index=True,
                         width='stretch', column_config={
                'Fréquence (Hz)': st.column_config.NumberColumn(format='%.2f'),
                'Force crête requise (N)': st.column_config.NumberColumn(format='%.3g'),
            })
        else:
            st.warning('Aucune bande assez stable numériquement pour estimer une force seuil dans ce scénario.')
        if noise_kind == 'Hypothèse de travail':
            st.warning('Le bruit de fond saisi est hypothétique. Les forces requises ne constituent pas encore une prévision pour le musée.')
        st.caption('Pour exploiter ces forces, il faudra mesurer la force harmonique réellement produite sur le fil de 0,762 mm, avec le montage, la commande et l’entrefer retenus. Une fiche de force d’adhérence sur une plaque d’acier ne suffit pas.')

    if st.checkbox('Illustrer un niveau avec une force crête saisie'):
        force = st.number_input('Force harmonique crête supposée (N)',
                                .0001, 10.0, .01, .001, format='%.4f')
        level_rows = []
        for result in summary:
            if not result['stable']:
                continue
            level_rows.extend((
                {'Fréquence (Hz)': result['frequency_hz'], 'Chevalet': label,
                 'Niveau conditionnel (dB SPL)': acoustic_level(result[field] * force)}
                for label, field in (('10 %', 'pressure_0.1'),
                                     ('22,5 %', 'pressure_0.225'))
            ))
        if level_rows:
            st.dataframe(pd.DataFrame(level_rows), hide_index=True, width='stretch',
                         column_config={
                'Fréquence (Hz)': st.column_config.NumberColumn(format='%.2f'),
                'Niveau conditionnel (dB SPL)': st.column_config.NumberColumn(format='%.1f'),
            })
        else:
            st.warning('Aucune bande assez stable numériquement pour afficher un niveau conditionnel dans ce scénario.')
        st.warning('Ce niveau dépend linéairement de la force saisie et du modèle acoustique idéalisé. Il n’intègre ni arrière ouvert, ni réflexions de la salle, ni autres sources ou visiteurs ; ce n’est pas un dB SPL prédit avec précision.')

    with st.expander('Méthode, convergence et limites'):
        st.markdown(r'''
**Chaîne calculée.** Les cordes sont des modes de fil tendu avec une petite correction de flexion. Leur contact linéarisé est couplé à une table de Kirchhoff–Love, résolue par Rayleigh–Ritz. Le panneau est pris continu à la jonction ; la traverse est une poutre solidaire si elle est activée. Les bords suivent la condition idéalisée choisie.

**Rayonnement.** Pour une face de table placée dans un écran rigide infini, la pression complexe au point d’écoute est obtenue par l’intégrale de Rayleigh :

\[p(\mathbf r)=-\frac{\rho_0\omega^2}{2\pi}\int_S w(\mathbf x)\frac{e^{-ikR}}{R}\,\mathrm dS,\qquad R=|\mathbf r-\mathbf x|.\]

Le calcul utilise \(\rho_0=1{,}20\;\mathrm{kg/m^3}\), \(c=343\;\mathrm{m/s}\), \(k=\omega/c\) et \(p_{\mathrm{rms}}=|p|/\sqrt2\). La surface est intégrée avec 48 × 48 points de Gauss. Le transfert est rapporté à **1 N crête** de force magnétique à 3 mm d’entrefer ; ce n’est pas la force étalonnée de l’électroaimant envisagé.

**Limite majeure.** Un écran rigide infini ne représente pas la table réelle dont le dos, la boîte et les fixations ne sont pas caractérisés. Il n’y a pas encore de couplage acoustique retour vers la table, de diffraction du cadre, de champ réverbéré ni de simulation de la salle. La variation entre ordres 10 et 12 ne quantifie que la convergence de la base mécanique, pas l’incertitude de toutes ces hypothèses.

**À ajouter dans une étude complète.** Éléments finis 2D de la table et des jonctions, caractérisation de l’effort électromagnétique dynamique, modèle acoustique de l’avant et de l’arrière, puis validation par mesures.
''')
        density = wire.rho * np.pi * wire.d ** 2 / 4
        fem_48 = string_fem_tension_modes(wire.L, wire.T, density, 48, 7)
        fem_96 = string_fem_tension_modes(wire.L, wire.T, density, 96, 7)
        analytic = (np.arange(1, 8) / (2 * wire.L)
                    * np.sqrt(wire.T / density))
        st.caption('Contrôle indépendant de la corde tendue par éléments finis 1D : les fréquences ci-dessous omettent seulement la faible correction de flexion du fil, présente dans le modèle principal.')
        st.dataframe(pd.DataFrame({
            'Mode': [1, 5, 7],
            'Analytique tension seule (Hz)': analytic[[0, 4, 6]],
            'EF · 48 éléments (Hz)': fem_48[[0, 4, 6]],
            'EF · 96 éléments (Hz)': fem_96[[0, 4, 6]],
        }), hide_index=True, width='stretch')

    export = frame.copy()
    export['Longueur corde (m)'] = length
    export['Fondamentale isolée visée (Hz)'] = fundamental
    export['Hauteur centre table (m)'] = center_height
    export['Distance avant (m)'] = front_distance
    export['Décalage latéral (m)'] = lateral_offset
    export['Hauteur oreille (m)'] = ear_height
    export['Masse chevalet supposée (kg)'] = bridge_mass
    export['Module panneau supposé (GPa)'] = modulus
    export['Masse volumique panneau supposée (kg/m3)'] = density
    export['Bords idéalisés'] = boundary
    export['Traverse centrale'] = support_enabled
    export['Modèle acoustique'] = 'Rayleigh, écran rigide infini, sans salle'
    st.download_button('Exporter cette comparaison en CSV',
                       export.to_csv(index=False).encode('utf-8-sig'),
                       'projection_acoustique_conditionnelle.csv', 'text/csv')
