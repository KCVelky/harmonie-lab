"""Scénario prévisionnel de l'instrument à plusieurs cordes."""

import json
import hashlib

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analyse_t12 import audio_info, spectrum
from audibilite import band_energy
from instrument_complet import (collective_convergence, combined_sound,
                                evaluate_instrument, evaluate_instrument_spectral,
                                example_strings, make_strings, preview_audio,
                                summarize_instrument)


st.set_page_config(page_title='Instrument complet · Harmonie Lab',
                   page_icon='🎼', layout='wide')
st.title('Instrument complet · étude prévisionnelle')
st.write('Une chaîne de calcul unique pour régler les cordes, vérifier la charge sur le bâtiment, comparer le chevalet et estimer le son direct au point d’écoute.')
st.warning('« Complet » décrit ici le parcours logiciel, pas une prédiction validée du niveau réel au musée. La force des aimants, la boîte, la salle et plusieurs propriétés mécaniques ne sont pas encore identifiées.')

with st.sidebar:
    st.header('Table et chevalet')
    st.caption('Table verticale de 5 × 8 pi, deux panneaux de contreplaqué de 1/8 po. Le centre est supposé à 15 m de haut.')
    bridge_mass = st.number_input('Masse du chevalet · hypothèse (kg)',
                                  0., 100., 5., .5)
    modulus = st.number_input('Module isotrope du panneau · hypothèse (GPa)',
                              1., 30., 10., .5)
    density = st.number_input('Masse volumique du panneau · hypothèse (kg/m³)',
                              300., 1200., 650., 25.)
    boundary = st.selectbox('Fixation idéalisée du bord',
                            ['Appuis simples', 'Encastrement'])
    support = st.checkbox('Traverse centrale solidaire', value=True)
    damping = st.number_input('Amortissement de la table · hypothèse ζ',
                              .001, .100, .012, .001, format='%.3f')
    if boundary == 'Appuis simples':
        resolution = st.selectbox('Contrôle de résolution mécanique',
                                  ['Haute résolution · ordres 34, 38 et 42',
                                   'Vérification approfondie · 38, 42, 46 et 50'])
        orders = ((34, 38, 42) if resolution.startswith('Haute')
                  else (38, 42, 46, 50))
        solver = 'spectral'
    else:
        resolution = st.selectbox('Contrôle de résolution mécanique',
                                  ['Exploratoire · ordres 10 et 12',
                                   'Exploratoire · ordres 12 et 14'])
        orders = ((10, 12) if resolution.startswith('Exploratoire · ordres 10')
                  else (12, 14))
        solver = 'modal'
        st.caption('Pour les bords encastrés, le calcul reste exploratoire : le solveur haute résolution actuel est réservé aux appuis simples.')
    st.divider()
    st.header('Contact corde–table')
    contact = st.number_input('Contact sur chaque corde (% de sa longueur)',
                              1., 30., 5., .5) / 100
    coupling = st.number_input('Raideur linéarisée du contact · hypothèse (N/m)',
                               0., 10000., 500., 50.)
    st.divider()
    st.header('Point d’écoute')
    center_height = st.number_input('Hauteur du centre de la table (m)',
                                    2., 30., 15., .5)
    front_distance = st.number_input('Distance devant la table (m)',
                                     .5, 30., 5., .5)
    lateral_offset = st.number_input('Décalage latéral (m)',
                                     -20., 20., 0., .5)
    ear_height = st.number_input('Hauteur des oreilles (m)', .5, 3., 1.6, .1)
    st.caption('Le calcul acoustique suppose la face avant dans un écran rigide infini : ni dos réel, ni réflexions de la salle.')

if 'instrument_rows' not in st.session_state:
    st.session_state.instrument_rows = example_strings()

tab_setup, tab_results, tab_signal, tab_method = st.tabs([
    '1 · Régler les cordes', '2 · Comparer et écouter le résultat',
    '3 · Vérifier T12', '4 · Méthode et validation'])

with tab_setup:
    st.subheader('Les 25 cordes')
    st.write('Chaque ligne fixe une longueur, une fondamentale de corde isolée, l’harmonique à exciter et un aimant. La colonne « Active » coupe uniquement la commande ; la corde reste présente dans le modèle mécanique et dans le bilan de charge.')
    count = st.number_input('Nombre de cordes à préparer', 1, 25, 25)
    if st.button('Créer un nouveau jeu de cordes'):
        st.session_state.instrument_rows = example_strings(count)
        st.session_state.pop('instrument_editor', None)
        st.session_state.pop('instrument_result', None)
    original = pd.DataFrame(st.session_state.instrument_rows)
    edited = st.data_editor(
        original, key='instrument_editor', hide_index=True, num_rows='fixed',
        width='stretch', column_config={
            'number': st.column_config.NumberColumn('Corde', disabled=True),
            'active': st.column_config.CheckboxColumn('Aimant actif'),
            'length_m': st.column_config.NumberColumn('Longueur (m)',
                                                       min_value=7.45, max_value=11.55,
                                                       step=.05, format='%.2f'),
            'fundamental_hz': st.column_config.NumberColumn('Fondamentale (Hz)',
                                                            min_value=7., max_value=20.,
                                                            step=.25, format='%.2f'),
            'harmonic': st.column_config.NumberColumn('Harmonique visé',
                                                      min_value=1, max_value=8, step=1),
            'magnet_pct': st.column_config.NumberColumn('Aimant sur la corde (% L)',
                                                        min_value=1., max_value=99.,
                                                        step=.5, format='%.2f'),
            'force_peak_n': st.column_config.NumberColumn('Force crête par aimant (N)',
                                                          min_value=0., max_value=10.,
                                                          step=.001, format='%.4f'),
        })
    st.caption('La force de 0,01 N proposée à l’ouverture est une valeur illustrative, non une donnée du modèle E-77-82-28AWG. La position initiale de l’aimant est un ventre de l’harmonique 7 ; modifiez-la avec le rang choisi.')
    records = edited.to_dict('records')
    try:
        _, string_info = make_strings(records, contact, coupling)
        total_tension = sum(item['tension_n'] for item in string_info)
        load_kgf = total_tension / 9.80665
        active_count = sum(item['active'] for item in string_info)
        metrics = st.columns(4)
        metrics[0].metric('Cordes présentes', len(string_info))
        metrics[1].metric('Aimants actifs', active_count)
        metrics[2].metric('Traction cumulée calculée', f'{load_kgf:.0f} kgf')
        metrics[3].metric('Enveloppe annoncée', '550 kgf')
        if load_kgf > 550:
            st.error('La traction calculée dépasse l’enveloppe de 550 kgf annoncée aux ingénieurs. La possibilité évoquée de 650–700 kgf doit être validée séparément ; elle ne modifie pas automatiquement cette limite.')
        else:
            st.success('La traction calculée reste sous 550 kgf pour ce jeu de cordes. Cela ne valide pas les ancrages, le cordier ni les charges dynamiques.')
        profile = pd.DataFrame([{
            'Corde': item['number'], 'Longueur (m)': item['length_m'],
            'Fondamentale isolée (Hz)': item['fundamental_hz'],
            'Rang': item['harmonic'], 'Force ciblée (Hz)': item['frequency_hz'],
            'Tension (N)': item['tension_n'],
            'Aimant · |sin(nπp)|': item['magnet_projection'],
            'Contact · |sin(nπβ)|': item['bridge_projection'],
        } for item in string_info])
        st.dataframe(profile, hide_index=True, width='stretch')
        st.caption('« Force ciblée » est la fréquence de la force appliquée par l’aimant, égale à la fréquence du mode isolé choisi. Elle ne devient pas une nouvelle fréquence propre de la table. Les facteurs sinus détectent les nœuds idéaux, sans donner le rendement sonore.')
    except ValueError as exc:
        st.error(str(exc))
        string_info = None

parameters = dict(contact_fraction=contact, coupling_n_m=coupling,
                  damping=damping, bridge_mass_kg=bridge_mass,
                  modulus_gpa=modulus, density_kg_m3=density,
                  boundary=boundary, support_enabled=support,
                  center_height_m=center_height,
                  receiver_xyz_m=(front_distance, lateral_offset, ear_height),
                  orders=orders)
scenario_key = (tuple(tuple(row[field] for field in original.columns) for row in records),
                tuple(parameters.items()), solver)


@st.cache_data(show_spinner=False, max_entries=4)
def calculate(key, rows, settings, method):
    engine = (evaluate_instrument_spectral if method == 'spectral'
              else evaluate_instrument)
    return engine([dict(row) for row in rows], **dict(settings))


with tab_results:
    st.subheader('Réponse collective de la table')
    st.write('Le calcul inclut toutes les cordes et leur couplage à la même table. Chaque aimant est évalué à la fréquence de son harmonique choisi ; les deux positions du chevalet sont comparées avec les mêmes commandes.')
    if st.button('Calculer les 25 cordes et les deux chevalets', type='primary',
                 disabled=string_info is None):
        try:
            with st.spinner('Assemblage des cordes, des deux positions et des deux résolutions…'):
                results, information = calculate(
                    scenario_key, tuple(tuple(row.items()) for row in records),
                    tuple(parameters.items()), solver)
            st.session_state.instrument_result = (results, information)
            st.session_state.instrument_result_key = scenario_key
        except ValueError as exc:
            st.error(str(exc))
    saved = (st.session_state.get('instrument_result')
             if st.session_state.get('instrument_result_key') == scenario_key else None)
    if saved is None:
        st.info('Lancez le calcul. Un changement de réglage rend les résultats précédents caducs.')
    else:
        results, information = saved
        summary = summarize_instrument(results, information)
        unstable = [row['number'] for row in summary if row['active'] and not row['stable']]
        if unstable:
            st.warning(f'Variation supérieure à 10 % sur les ordres étudiés pour {len(unstable)} corde(s). Leur classement individuel est incertain ; le niveau de toutes les cordes est contrôlé séparément ci-dessous.')
        else:
            st.success('Les transferts de toutes les cordes actives varient de moins de 10 % entre les ordres mécaniques testés. Cela ne valide ni les propriétés matérielles, ni le rayonnement réel.')
        collective = collective_convergence(results, information)
        convergence_columns = st.columns(2)
        for column, position, label in zip(convergence_columns, (.10, .225),
                                           ('10 % du haut', '22,5 % du haut')):
            variation = collective[position]['relative_span']
            column.metric(f'Variation du son collectif · {label}',
                          f'{100 * variation:.1f} %')
        if all(item['relative_span'] <= .10 for item in collective.values()):
            st.success('Le niveau collectif non synchronisé varie de moins de 10 % entre les résolutions affichées. Les dB conditionnels peuvent être examinés, sous les hypothèses physiques indiquées.')
        else:
            st.warning('Le niveau collectif varie encore de plus de 10 % : les dB concernés resteront masqués. Essayez la vérification approfondie ou revoyez le scénario.')
        st.caption('La convergence individuelle porte sur chaque raie ; la convergence collective porte sur la somme énergétique de toutes les raies. Une faible raie instable peut donc coexister avec un niveau collectif stable. Aucune des deux ne mesure l’incertitude sur les aimants, le bois ou la salle.')
        readable = [row for row in summary if row['active'] and row['stable']]
        favors_10 = sum(row['pressure_0.1'] > 1.2 * row['pressure_0.225']
                        for row in readable)
        favors_225 = sum(row['pressure_0.225'] > 1.2 * row['pressure_0.1']
                         for row in readable)
        indicators = st.columns(4)
        indicators[0].metric('Cordes actives interprétables',
                             f'{len(readable)} / {sum(row["active"] for row in summary)}')
        indicators[1].metric('10 % favorisé', favors_10)
        indicators[2].metric('22,5 % favorisé', favors_225)
        indicators[3].metric('Écart inférieur à 20 %',
                             len(readable) - favors_10 - favors_225)
        st.caption('« Favorisé » signifie ici un transfert calculé au moins 20 % plus élevé, pour la même force. Ce seuil est une règle de lecture choisie, pas une garantie d’audibilité. Les cordes non convergées sont exclues du comptage.')
        comparison = pd.DataFrame([{
            'Corde': row['number'], 'Hz': row['frequency_hz'],
            'Harmonique': row['harmonic'],
            '10 % · Pa RMS/N crête': row['pressure_0.1'],
            '22,5 % · Pa RMS/N crête': row['pressure_0.225'],
            'Convergence 10 %': row['convergence_0.1'],
            'Convergence 22,5 %': row['convergence_0.225'],
            'Résolution': 'à affiner' if not row['stable'] else 'suffisante',
        } for row in summary if row['active']])
        st.dataframe(comparison, hide_index=True, width='stretch', column_config={
            '10 % · Pa RMS/N crête': st.column_config.NumberColumn(format='%.3g'),
            '22,5 % · Pa RMS/N crête': st.column_config.NumberColumn(format='%.3g'),
            'Convergence 10 %': st.column_config.NumberColumn(format='%.1%'),
            'Convergence 22,5 %': st.column_config.NumberColumn(format='%.1%'),
        })
        if not comparison.empty:
            figure = go.Figure()
            for name, field, color in (
                ('10 % du haut', '10 % · Pa RMS/N crête', '#65a9ff'),
                ('22,5 % du haut', '22,5 % · Pa RMS/N crête', '#f7a65c')):
                figure.add_bar(name=name, x=comparison['Corde'],
                               y=comparison[field], marker_color=color)
            figure.update_layout(barmode='group', height=370,
                                 xaxis_title='Corde',
                                 yaxis_title='Transfert acoustique direct (Pa RMS/N crête)',
                                 margin=dict(l=15, r=15, t=20, b=15))
            st.plotly_chart(figure, width='stretch')
        st.caption('La pression par newton tient compte de la phase spatiale du panneau : deux zones qui vibrent fortement peuvent s’annuler acoustiquement. Une grande accélération de table ne garantit donc pas un grand niveau au public.')

        st.subheader('Préécoute de toutes les cordes commandées')
        st.write('Cette écoute synthétise les raies calculées au point choisi et normalise le fichier pour qu’il soit audible sur votre appareil. Elle permet de comparer les timbres et les battements, pas le volume réel de l’installation.')
        listening_position = st.radio('Chevalet pour la préécoute',
                                      ['10 % du haut', '22,5 % du haut'],
                                      horizontal=True)
        fraction = .10 if listening_position.startswith('10') else .225
        try:
            audio = preview_audio(summary, fraction)
            st.audio(audio, format='audio/wav')
            st.download_button('Télécharger cette préécoute (WAV)', audio,
                               'instrument_complet_prevision.wav', 'audio/wav')
        except ValueError as exc:
            st.info(str(exc))
        if unstable:
            st.warning('Préécoute exploratoire : au moins une raie ne converge pas assez pour prédire fidèlement sa balance sonore.')

        if st.checkbox('Afficher les dB avec les forces saisies',
                       help='À activer seulement pour un scénario de force explicitement supposé ou mesuré.'):
            provenance = st.radio('Provenance de la force crête saisie',
                                  ['Hypothèse de travail', 'Mesure sur le fil et le montage retenus'],
                                  horizontal=True)
            background = st.number_input('Bruit de fond au même point et dans la même plage de fréquences (dB SPL RMS)',
                                         0., 110., 40., 1.)
            aggregate = []
            for phase_locked in (False, True):
                stability = collective_convergence(results, information,
                                                   phase_locked=phase_locked)
                for position in (.10, .225):
                    if stability[position]['relative_span'] <= .10:
                        sound = combined_sound(summary, position, phase_locked=phase_locked)
                        aggregate.append({
                            'Chevalet': f'{100 * position:g} %',
                            'Hypothèse de phase': ('Sources non synchronisées'
                                                   if not phase_locked else
                                                   'Même phase de commande aux fréquences identiques'),
                            'Source au point d’écoute (dB SPL)': sound['level_db_spl'],
                            'Écart avec le fond saisi (dB)': sound['level_db_spl'] - background,
                            'Variation numérique': stability[position]['relative_span'],
                        })
            if aggregate:
                st.dataframe(pd.DataFrame(aggregate), hide_index=True,
                             width='stretch', column_config={
                    'Source au point d’écoute (dB SPL)': st.column_config.NumberColumn(format='%.1f'),
                    'Écart avec le fond saisi (dB)': st.column_config.NumberColumn(format='%+.1f'),
                    'Variation numérique': st.column_config.NumberColumn(format='%.1%'),
                })
                st.caption('Les contributions à des fréquences différentes sont additionnées en énergie moyenne. À fréquence strictement égale, la somme est complexe si les commandes partagent une phase connue ; le cas non synchronisé additionne les énergies. Ce sont des scénarios, pas des bornes universelles.')
                if provenance == 'Hypothèse de travail':
                    st.warning('Ces dB ne sont pas une prédiction absolue validée. La force et le bruit de fond sont hypothétiques ; le modèle de rayonnement ignore la boîte et la salle.')
                else:
                    st.warning('Même avec une force mesurée, l’écran acoustique infini, la table et la salle restent non validés. Une mesure au micro est nécessaire pour confronter le résultat au réel.')
                chosen = st.selectbox('Voir les raies calculées pour',
                                      ['10 % du haut', '22,5 % du haut'])
                selected = .10 if chosen.startswith('10') else .225
                lines = combined_sound(summary, selected, phase_locked=True)['lines']
                st.dataframe(pd.DataFrame(lines).rename(columns={
                    'frequency_hz': 'Fréquence (Hz)',
                    'contributors': 'Cordes à cette fréquence',
                    'pressure_rms_pa': 'Pression RMS (Pa)',
                    'level_db_spl': 'Niveau de la raie (dB SPL)',
                }), hide_index=True, width='stretch')
            else:
                st.error('Aucun niveau collectif assez stable numériquement pour ce scénario.')

        export = comparison.copy()
        st.download_button('Exporter la comparaison (CSV)',
                           export.to_csv(index=False).encode('utf-8-sig'),
                           'instrument_complet_comparaison.csv', 'text/csv')
        st.download_button('Exporter les réglages (JSON)',
                           json.dumps({'cordes': records, 'hypotheses': parameters},
                                      ensure_ascii=False, indent=2).encode('utf-8'),
                           'instrument_complet_configuration.json',
                           'application/json')

with tab_signal:
    st.subheader('Le bâtiment fournit-il un signal aux fréquences choisies ?')
    st.write('Déposez T12 pour confronter les fréquences visées au spectre enregistré. Les nombres du WAV sont numériques : sans gain complet de la chaîne d’acquisition, ils ne sont ni une accélération étalonnée du bâtiment ni une force d’aimant.')
    upload = st.file_uploader('Enregistrement T12 (WAV ou ZIP)',
                              type=['wav', 'zip'], key='complete_t12')
    if upload is not None:
        try:
            payload = upload.getvalue()
            upload_id = hashlib.sha256(payload).hexdigest()
            info = audio_info(payload, upload.name)
            channel = st.selectbox('Canal à analyser',
                                   list(range(1, info['channels'] + 1)))
            if st.button('Analyser les bandes de T12'):
                with st.spinner('Lecture du spectre…'):
                    spectral = spectrum(payload, upload.name, channel - 1)
                st.session_state.instrument_spectrum = spectral
                st.session_state.instrument_spectrum_key = (upload_id, channel)
            spectral = (st.session_state.get('instrument_spectrum')
                        if st.session_state.get('instrument_spectrum_key') ==
                        (upload_id, channel) else None)
            if spectral is not None and string_info is not None:
                rows = []
                for item in string_info:
                    if not item['active']:
                        continue
                    try:
                        power = band_energy(spectral, item['frequency_hz'], 1.)
                    except ValueError:
                        power = np.nan
                    rows.append({'Corde': item['number'],
                                 'Fréquence visée (Hz)': item['frequency_hz'],
                                 'Énergie numérique T12 ±1 Hz': power})
                frame = pd.DataFrame(rows)
                if not frame.empty:
                    st.dataframe(frame, hide_index=True, width='stretch')
                    st.caption('Une bande riche dans T12 est une possibilité d’excitation. Elle ne garantit pas la force électromagnétique ni l’audibilité. Si la force varie comme le carré du courant sans polarisation, sa fréquence peut être doublée : ce tableau compare seulement les fréquences de force que vous avez choisies.')
        except ValueError as exc:
            st.error(str(exc))

with tab_method:
    st.subheader('Ce que le calcul représente')
    st.markdown(r'''
1. **Corde isolée.** La tension est calculée à partir de sa longueur, de sa fondamentale cible, du diamètre de 0,762 mm et d’une faible correction de flexion. Les harmoniques proviennent ensuite du modèle de fil tendu avec cette correction. Les 25 tensions, y compris celles des cordes non commandées, sont sommées pour l’enveloppe statique.
2. **Aimant et contact.** La force harmonique crête est une entrée, pas une sortie du modèle électromagnétique. La projection de l’aimant sur le mode (n) vaut \(\sin(n\pi p)\), et celle du contact corde–chevalet \(\sin(n\pi\beta)\). La raideur de contact est linéarisée. La phase et l’amplitude réelles peuvent dépendre de la commande, de l’entrefer, du courant et de la saturation.
3. **Structure.** Toutes les cordes sont couplées à une même table de Kirchhoff–Love. Avec les appuis simples, une base sinusoïdale haute résolution donne exactement les matrices de masse et de raideur de la plaque idéale ; la traverse, la masse du chevalet et les contacts sont ajoutés par leurs contributions énergétiques. La réponse harmonique est résolue directement, avec un facteur de perte structurel \(\eta=2\zeta\) pour la plaque et les cordes. Avec les bords encastrés, la page conserve l’ancien calcul modal Rayleigh–Ritz à plus basse résolution : les deux choix de bords ne diffèrent donc pas uniquement par la fixation. Il ne s’agit pas d’un maillage éléments finis 2D. Les deux panneaux sont supposés parfaitement continus à la jonction. Le chevalet est représenté par sa masse répartie, sans flexion propre.
4. **Rayonnement.** La pression directe au point d’écoute provient de l’intégrale de Rayleigh sur une face dans un écran rigide infini :

   \[p(\mathbf r)=-\frac{\rho_0\omega^2}{2\pi}\int_S w(\mathbf x)\frac{e^{-ikR}}{R}\,\mathrm dS.\]

   La pression complexe est convertie en RMS, puis en dB SPL par rapport à 20 µPa. Les contributions à des fréquences différentes sont additionnées en énergie. Le dos, la boîte réelle, le couplage acoustique retour, les réflexions et la présence du public ne sont pas calculés.
5. **Convergence.** Les ordres choisis dans la barre latérale sont comparés de deux façons : pression par corde et pression RMS de l’ensemble. La variation est \((\max p-\min p)/\max p\) sur tous les ordres. Les dB collectifs ne s’affichent que si le total correspondant varie de moins de 10 %. Cette stabilité numérique ne valide pas les paramètres physiques ; certaines raies peuvent rester incertaines même lorsque le total est stable.
''')
    st.subheader('Ce qu’il faut encore pour une prévision crédible')
    st.dataframe(pd.DataFrame([
        {'Donnée': 'Force harmonique sur le fil choisi', 'État': 'Non mesurée',
         'Pourquoi': 'Fixe l’échelle absolue des dB ; la force d’adhérence catalogue ne suffit pas.'},
        {'Donnée': 'Panneaux et jonction réelle', 'État': 'Hypothèses',
         'Pourquoi': 'Module, masse et amortissement déplacent les résonances.'},
        {'Donnée': 'Chevalet, appuis et boîte', 'État': 'Hypothèses',
         'Pourquoi': 'Modifient la vibration et le rayonnement avant/arrière.'},
        {'Donnée': 'Salle et position du public', 'État': 'Non caractérisées',
         'Pourquoi': 'Les réflexions et le bruit de fond changent ce qui est entendu.'},
        {'Donnée': 'Commande et étalonnage T12', 'État': 'Partiels',
         'Pourquoi': 'Le spectre numérique seul ne détermine pas le courant ni la force.'},
        {'Donnée': 'Essai au micro, instrument en marche/arrêt', 'État': 'À venir',
         'Pourquoi': 'Vérifie finalement le niveau sonore et le modèle.'},
    ]), hide_index=True, width='stretch')
    st.info('La page sert à choisir des essais prometteurs et à documenter les hypothèses pour le concours. Elle ne remplace pas l’accord des ingénieurs pour les charges ni une mesure d’audibilité en salle.')
