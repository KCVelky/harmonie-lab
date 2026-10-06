"""Parcours de preuve pour l'audibilité du scénario Sandra."""

from dataclasses import replace

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analyse_t12 import audio_info, spectrum
from audibilite import (band_energy, comparison_variants, geometry_factors,
                        measured_emergence, museum_case,
                        source_spl_from_on_off, weighted_mechanical_index)
from etude_sandra import compare_positions, summarize_comparison
from physics import string_frequencies


st.set_page_config(page_title='Audibilité · Harmonie Lab', page_icon='🔊', layout='wide')
st.title('Audibilité · étude pour Sandra')
st.write('Une corde, deux positions de chevalet et une chaîne de preuve allant du signal T12 jusqu’au micro dans la salle.')
st.info('Les calculs actuels établissent une **possibilité mécanique**, pas encore un niveau sonore entendu par les visiteurs. Les champs marqués « hypothèse » doivent être identifiés ou mesurés avant une conclusion acoustique.')


@st.cache_data(show_spinner=False)
def nominal_study(plate, wire, support):
    return compare_positions(plate, wire, support)


@st.cache_data(show_spinner=False)
def sensitivity_study(plate, wire, support):
    return comparison_variants(plate, wire, support)


with st.sidebar:
    st.header('Scénario étudié')
    st.caption('Table verticale 5 × 8 pi, deux panneaux de 1/8 po, jonction centrale collée supposée parfaite. Hauteur d’installation : environ 15 m.')
    length = st.number_input('Longueur vibrante de la corde (m)', min_value=8., max_value=12., value=10., step=.25)
    fundamental = st.number_input('Fondamentale visée (Hz)', min_value=7., max_value=15., value=12., step=.25)
    magnet_pct = st.number_input('Aimant depuis une extrémité (% de L)', min_value=1., max_value=99., value=10., step=.5)
    contact_pct = st.number_input('Contact corde–chevalet (% de L)', min_value=1., max_value=30., value=5., step=.5)
    with st.expander('Hypothèses mécaniques non mesurées'):
        coupling = st.number_input('Raideur de contact (N/m)', min_value=0., max_value=10000., value=500., step=50.)
        force = st.number_input('Force harmonique crête par aimant (N)', min_value=.0001, max_value=1., value=.01, step=.001, format='%.4f')
        plate_damping = st.number_input('Amortissement de la table ζ', min_value=.001, max_value=.10, value=.012, step=.001, format='%.3f')
    st.caption('Matériau, bords, traverse, force et contact du cas initial restent des hypothèses de calcul, pas des mesures de l’installation.')

try:
    plate, wire, support = museum_case(length, fundamental, magnet_pct/100,
                                       contact_pct/100, coupling, force, plate_damping)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

frequencies = string_frequencies(wire, 7)
targets = {5: float(frequencies[4]), 7: float(frequencies[6])}
cols = st.columns(4)
cols[0].metric('Tension calculée · une corde', f'{wire.T:.1f} N')
cols[1].metric('Fondamentale isolée', f'{frequencies[0]:.1f} Hz')
cols[2].metric('5ᵉ harmonique isolée', f'{targets[5]:.1f} Hz')
cols[3].metric('7ᵉ harmonique isolée', f'{targets[7]:.1f} Hz')
st.caption('La tension et les harmoniques ci-dessus décrivent la corde isolée. Le chevalet et la table perturbent ses modes couplés. Pour 25 cordes identiques, la traction serait 25 × celle d’une corde ; ce n’est pas une prévision de la charge réelle des 25 cordes de longueurs différentes.')
if wire.T > 5400/25:
    st.warning('Cette corde dépasse 216 N, soit la moyenne par corde correspondant à l’enveloppe annoncée de 5,4 kN pour 25 cordes. Cela ne suffit pas à conclure sur la charge totale : chaque corde doit être calculée séparément.')

first, second, third, fourth = st.tabs([
    '1 · Corde et table', '2 · Signal T12', '3 · Robustesse', '4 · Preuve acoustique'
])

with first:
    st.subheader('Choisir une excitation qui atteint la table')
    geometry = []
    for rank, frequency in targets.items():
        at_magnet, at_contact = geometry_factors(rank, wire.p1, wire.beta)
        geometry.append({'Harmonique': rank, 'Fréquence isolée (Hz)': frequency,
                         'Aimant · |sin(nπp)|': at_magnet,
                         'Contact · |sin(nπβ)|': at_contact})
    st.dataframe(pd.DataFrame(geometry), hide_index=True, width='stretch',
                 column_config={'Fréquence isolée (Hz)': st.column_config.NumberColumn(format='%.2f'),
                                'Aimant · |sin(nπp)|': st.column_config.NumberColumn(format='%.3f'),
                                'Contact · |sin(nπβ)|': st.column_config.NumberColumn(format='%.3f')})
    st.caption('Ces sinus sont les projections sur les modes de la corde isolée : zéro indique un nœud idéal. Ils ne sont ni un rendement acoustique, ni une prédiction de force magnétique.')
    if st.button('Calculer la comparaison 10 % / 22,5 %', type='primary'):
        with st.spinner('Calcul aux résolutions 10, 12 et 14…'):
            st.session_state.audibility_nominal = nominal_study(plate, wire, support)
            st.session_state.audibility_nominal_key = (plate, wire, support)
    rows = st.session_state.get('audibility_nominal') if st.session_state.get('audibility_nominal_key') == (plate, wire, support) else None
    summary = summarize_comparison(rows) if rows else None
    if summary:
        table = pd.DataFrame([{'Harmonique': r['harmonic'], 'Fréquence de force (Hz)': r['force_hz'],
                              'Table · 10 % (m/s²)': r['rms_10'],
                              'Table · 22,5 % (m/s²)': r['rms_22_5'],
                              'Rapport 10 % / 22,5 %': r['ratio_10_over_22_5'],
                              'Convergence 10 %': r['convergence_10'],
                              'Convergence 22,5 %': r['convergence_22_5'],
                              'Lecture': r['verdict']} for r in summary])
        st.dataframe(table, hide_index=True, width='stretch', column_config={
            'Fréquence de force (Hz)': st.column_config.NumberColumn(format='%.2f'),
            'Table · 10 % (m/s²)': st.column_config.NumberColumn(format='%.4g'),
            'Table · 22,5 % (m/s²)': st.column_config.NumberColumn(format='%.4g'),
            'Rapport 10 % / 22,5 %': st.column_config.NumberColumn(format='%.2f'),
            'Convergence 10 %': st.column_config.NumberColumn(format='%.1%'),
            'Convergence 22,5 %': st.column_config.NumberColumn(format='%.1%')})
        chart = go.Figure()
        for label, field in [('10 %', 'rms_10'), ('22,5 %', 'rms_22_5')]:
            chart.add_bar(name=label, x=[f'{r["force_hz"]:.1f} Hz' for r in summary],
                          y=[r[field] for r in summary])
        chart.update_layout(barmode='group', height=330,
                            yaxis_title='Accélération spatiale quadratique · amplitude crête (m/s²)')
        st.plotly_chart(chart, width='stretch')
        if any(not r['stable'] for r in summary):
            st.warning('La résolution ne converge pas suffisamment pour au moins une fréquence : ne pas classer les positions sur cette ligne.')
        st.caption('Le même effort harmonique supposé est appliqué aux deux configurations. La vibration spatiale quadratique ne mesure pas le rayonnement sonore. Le chevalet reste à la même position sur la corde ; seul son emplacement sur la table change.')
        st.download_button('Télécharger les résultats mécaniques', table.to_csv(index=False).encode('utf-8-sig'),
                           'audibilite_comparaison.csv', 'text/csv')
    else:
        st.info('Lancez le calcul pour obtenir la comparaison mécanique. Aucun résultat n’est conservé si vous changez le scénario.')

with second:
    st.subheader('Chercher une excitation disponible dans T12')
    uploaded = st.file_uploader('WAV T12 ou archive ZIP contenant un WAV', type=['wav', 'zip'])
    st.caption('Le fichier de chantier est exploratoire et son étalonnage est inconnu. L’énergie calculée est celle du fichier numérique, pas une accélération absolue du bâtiment.')
    mapping = st.radio('Fréquence de la force magnétique',
                       ['Même fréquence que la commande · linéarisation à vérifier',
                        'Deux fois la fréquence de la commande · cas quadratique idéal'],
                       horizontal=True)
    factor = 2 if mapping.startswith('Deux') else 1
    gain5 = st.number_input('Gain du filtre MAX/MSP vers le 5ᵉ mode (dB)', min_value=-40., max_value=40., value=0., step=1.)
    gain7 = st.number_input('Gain du filtre MAX/MSP vers le 7ᵉ mode (dB)', min_value=-40., max_value=40., value=0., step=1.)
    energies = None
    if uploaded is not None:
        try:
            data = uploaded.getvalue()
            info = audio_info(data, uploaded.name)
            st.write(f'**{info["name"]}** · {info["duration"]:.1f} s · {info["channels"]} canal(aux) · {info["sample_rate"]} échantillons/s')
            channel = st.selectbox('Canal à analyser', list(range(info['channels'])),
                                   format_func=lambda i: f'Canal {i+1}')
            if st.button('Analyser T12'):
                with st.spinner('Lecture du canal sélectionné…'):
                    st.session_state.audibility_spectrum = spectrum(data, uploaded.name, channel)
                    st.session_state.audibility_spectrum_key = (uploaded.name, len(data), channel)
            result = (st.session_state.get('audibility_spectrum')
                      if st.session_state.get('audibility_spectrum_key') == (uploaded.name, len(data), channel)
                      else None)
            if result:
                band_rows = []
                energies = {}
                for rank, frequency in targets.items():
                    command_hz = frequency/factor
                    energy = band_energy(result, command_hz, 1.)
                    energies[rank] = energy
                    band_rows.append({'Harmonique': rank, 'Force souhaitée (Hz)': frequency,
                                      'Bande recherchée dans T12 (Hz)': command_hz,
                                      'Énergie numérique ±1 Hz': energy,
                                      'Gain de filtre proposé (dB)': gain5 if rank == 5 else gain7})
                st.dataframe(pd.DataFrame(band_rows), hide_index=True, width='stretch',
                             column_config={'Énergie numérique ±1 Hz': st.column_config.NumberColumn(format='%.3g')})
                x = result['frequency_hz']; power = result['power']
                visible = (x >= 5) & (x <= 150)
                y = 10*np.log10(np.maximum(power[visible]/max(float(np.max(power[visible])), 1e-30), 1e-12))
                figure = go.Figure(go.Scatter(x=x[visible], y=y, mode='lines', name='T12'))
                figure.update_layout(height=320, xaxis_title='Fréquence du WAV (Hz)',
                                     yaxis_title='Densité spectrale relative (dB)')
                st.plotly_chart(figure, width='stretch')
                st.caption('L’énergie est intégrée dans une bande de 2 Hz. Un pic à 60 Hz pourrait provenir du réseau électrique ou du chantier : ce seul enregistrement ne démontre ni une vibration permanente du bâtiment, ni un effet du nombre de visiteurs.')
                if factor == 1 and summary and all(r['stable'] for r in summary):
                    try:
                        index = weighted_mechanical_index(summary, energies, {5: gain5, 7: gain7})
                        ratio = index['10 %']/max(index['22,5 %'], 1e-30)
                        st.metric('Indice mécanique T12 · 10 % / 22,5 %', f'{ratio:.2f} ×')
                        st.caption('Indice conditionnel : même conversion commande → force aux deux fréquences, filtre plat dans chaque bande, et force linéaire à la fréquence de commande. Le facteur inconnu commun s’annule dans ce rapport. Ce n’est ni un niveau sonore ni une probabilité d’audibilité.')
                    except ValueError as exc:
                        st.warning(str(exc))
                elif factor == 2:
                    st.warning('Dans le cas d’une force quadratique à 2f, l’énergie de la force dépend du carré du signal temporel et de ses mélanges fréquentiels. Les énergies T12 à f/2 ne suffisent pas à calculer un indice de réponse : il faut mesurer la force réelle ou modéliser toute la chaîne de commande.')
        except (ValueError, TypeError, KeyError) as exc:
            st.error('Analyse T12 impossible : ' + str(exc))
    else:
        st.info('Déposez le WAV pour établir quelles bandes sont présentes dans cette captation. Aucun fichier T12 n’est inclus dans l’application publique.')

with third:
    st.subheader('Vérifier si le choix résiste aux hypothèses')
    st.write('Le collage, le cadre, l’amortissement et la raideur de la traverse ne sont pas identifiés. Un bon résultat nominal ne suffit donc pas à départager définitivement 10 % et 22,5 %.')
    if st.button('Comparer les variantes de fixation et d’amortissement'):
        with st.spinner('Calcul de quatre scénarios aux résolutions 12 et 14…'):
            st.session_state.audibility_sensitivity = sensitivity_study(plate, wire, support)
            st.session_state.audibility_sensitivity_key = (plate, wire, support)
    variants = (st.session_state.get('audibility_sensitivity')
                if st.session_state.get('audibility_sensitivity_key') == (plate, wire, support)
                else None)
    if variants:
        frame = pd.DataFrame([{'Hypothèse': r['case'], 'Force (Hz)': r['force_hz'],
                              'Rapport vibration 10 % / 22,5 %': r['ratio_10_over_22_5'],
                              'Convergence': 'suffisante' if r['stable'] else 'insuffisante',
                              'Lecture': r['verdict']} for r in variants])
        st.dataframe(frame, hide_index=True, width='stretch', column_config={
            'Force (Hz)': st.column_config.NumberColumn(format='%.1f'),
            'Rapport vibration 10 % / 22,5 %': st.column_config.NumberColumn(format='%.2f')})
        for rank in (5, 7):
            group = [r for r in variants if r['harmonic'] == rank]
            if any(not r['stable'] for r in group):
                st.warning(f'Harmonique {rank} : au moins une variante ne converge pas. Aucun classement robuste ne peut être affirmé.')
                continue
            verdicts = {r['verdict'] for r in group}
            if len(verdicts) == 1 and 'plus élevé' in next(iter(verdicts)):
                st.success(f'Harmonique {rank} : la même position donne plus de vibration globale dans toutes les variantes testées. Ce n’est pas un verdict acoustique.')
            elif len({v for v in verdicts if 'plus élevé' in v}) > 1:
                st.warning(f'Harmonique {rank} : le classement s’inverse selon l’hypothèse. Garder les deux positions pour l’essai.')
            else:
                st.info(f'Harmonique {rank} : les variantes comprennent des réponses proches ; pas de préférence mécanique robuste.')
        st.caption('Les variantes ne sont pas des limites physiques garanties du montage réel. Le modèle suppose une plaque continue et un comportement linéaire ; il n’identifie pas le collage ni les fixations effectivement construits.')
    else:
        st.info('Lancez la comparaison pour voir si une recommandation est robuste aux hypothèses du modèle.')

with fourth:
    st.subheader('Ce qui manque pour conclure sur le son dans la salle')
    st.write('La synthèse audio de l’application est normalisée : son volume ne permet pas de juger du volume réel de l’instrument. Le calcul mécanique n’inclut pas le rayonnement de la table, son dos ouvert, la salle, la distance aux visiteurs ni le bruit ambiant.')
    st.markdown('**État actuel :** modes audibles accessibles sur la corde · réponse mécanique calculable · niveau acoustique au public **non déterminé**.')
    st.markdown('**Mesure minimale pour le jury :** à une position de visiteurs représentative, relever dans la même bande de 2 Hz le niveau acoustique avec l’aimant en marche, puis à l’arrêt. Refaire à 60 et 84 Hz et aux deux positions de chevalet. Mesurer aussi la force harmonique appliquée ou son équivalent étalonné.')
    if st.checkbox('Je dispose de mesures acoustiques et d’une force d’excitation étalonnées'):
        st.caption('Entrer des niveaux dB SPL RMS mesurés au même microphone, au même endroit et dans la même bande autour d’une seule fréquence. La soustraction énergétique suppose un fond stationnaire et non corrélé à la source ; l’extrapolation suppose une force et une réponse linéaires.')
        f_choice = st.selectbox('Fréquence étudiée', [f'{r}: {targets[r]:.2f} Hz' for r in (5, 7)])
        bridge_choice = st.selectbox('Chevalet depuis le haut', ['10 %', '22,5 %'])
        on_db = st.number_input('Aimant en marche · niveau dans la bande (dB SPL)', min_value=-20., max_value=150., value=60., step=.5)
        off_db = st.number_input('Aimant arrêté · même bande (dB SPL)', min_value=-20., max_value=150., value=50., step=.5)
        ref_force = st.number_input('Force crête mesurée pendant le test (N)', min_value=.0001, max_value=100., value=.01, step=.001, format='%.4f')
        planned_force = st.number_input('Force crête prévue avec le réglage retenu (N)', min_value=.0001, max_value=100., value=.01, step=.001, format='%.4f')
        uncertainty = st.number_input('Marge conservatrice choisie pour l’incertitude (dB)', min_value=0., max_value=30., value=3., step=.5,
                                      help='Valeur de prudence à justifier par la variabilité observée. Ce n’est pas un intervalle statistique calculé.')
        try:
            source_db = source_spl_from_on_off(on_db, off_db)
            result = measured_emergence(source_db, off_db, ref_force, planned_force, uncertainty)
            c1, c2, c3 = st.columns(3)
            c1.metric('Source estimée au micro', f'{result["projected_source_spl_db"]:.1f} dB SPL')
            c2.metric('Source – bruit de fond', f'{result["margin_db"]:+.1f} dB')
            c3.metric('Avec incertitude retenue', f'{result["conservative_margin_db"]:+.1f} dB')
            if planned_force/ref_force > 2 or planned_force/ref_force < .5:
                st.warning('Extrapolation de force supérieure à un facteur 2 : vérifier expérimentalement que la chaîne reste linéaire. Les électroaimants peuvent être non linéaires.')
            if result['conservative_margin_db'] > 0:
                st.success(f'À {f_choice}, chevalet {bridge_choice} : dans cette bande et à ce microphone, la source estimée dépasse le fond même avec l’incertitude saisie. Cela soutient l’audibilité locale, sans garantir la perception par tous les visiteurs.')
            else:
                st.warning('Le contraste avec le fond n’est pas établi de façon robuste pour cette mesure. Ne pas conclure que l’instrument est inaudible ailleurs ou à une autre fréquence.')
            st.caption('Soustraction d’énergie : L_source = 10 log₁₀(10^(L_marche/10) − 10^(L_arrêt/10)). Extrapolation linéaire : ΔL = 20 log₁₀(F_prévue/F_test). Ces relations supposent une source stable, un fond comparable et le même montage et emplacement du micro.')
        except ValueError as exc:
            st.warning(str(exc))
    else:
        st.warning('Aucune mesure acoustique étalonnée saisie : l’application ne donne volontairement ni dB SPL prédit ni pourcentage de chance d’être entendu.')
    st.markdown('**Conclusion transmissible aujourd’hui :** le principe d’excitation des modes supérieurs est cohérent et des réglages mécaniques sont comparables. **Conclusion à confirmer par essai :** leur niveau sonore au public et leur contraste avec l’ambiance du musée.')
