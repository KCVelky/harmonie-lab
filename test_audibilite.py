"""Vérifications des grandeurs utilisées dans la page d'audibilité."""

from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from audibilite import (band_energy, geometry_factors, measured_emergence,
                        museum_case, source_spl_from_on_off,
                        weighted_mechanical_index)
from physics import string_frequencies


def test_reference_case_and_geometry():
    _, wire, _ = museum_case()
    np.testing.assert_allclose(wire.T, 206.49, atol=.02)
    np.testing.assert_allclose(string_frequencies(wire, 7)[[4, 6]], [60, 84], atol=.01)
    at_magnet, at_contact = geometry_factors(5, .10, .05)
    assert at_magnet == pytest.approx(1.)
    assert at_contact == pytest.approx(np.sqrt(.5))
    assert geometry_factors(5, .20, .05)[0] < 1e-14


def test_band_energy_and_weighted_index():
    spectral = {'frequency_hz': np.arange(0., 11.),
                'power': np.full(11, 2.)}
    assert band_energy(spectral, 5., 1.) == pytest.approx(6.)
    summary = [{'harmonic': 5, 'stable': True, 'rms_10': 2., 'rms_22_5': 1.},
               {'harmonic': 7, 'stable': True, 'rms_10': 1., 'rms_22_5': 2.}]
    index = weighted_mechanical_index(summary, {5: 3., 7: 1.}, {5: 0., 7: 0.})
    assert index['10 %'] == pytest.approx(np.sqrt(13/4))
    assert index['22,5 %'] == pytest.approx(np.sqrt(7/4))
    boosted = weighted_mechanical_index(summary, {5: 3., 7: 1.}, {5: 0., 7: 10.})
    assert boosted['22,5 %'] > boosted['10 %']
    summary[0]['stable'] = False
    with pytest.raises(ValueError, match='Convergence'):
        weighted_mechanical_index(summary, {5: 3., 7: 1.})


def test_measured_sound_requires_detectable_on_off_difference():
    source = source_spl_from_on_off(60., 50.)
    assert source == pytest.approx(59.542425, abs=1e-5)
    outcome = measured_emergence(source, 50., .01, .02, 3.)
    assert outcome['projected_source_spl_db'] == pytest.approx(source+20*np.log10(2))
    assert outcome['conservative_margin_db'] == pytest.approx(
        outcome['margin_db']-3.)
    with pytest.raises(ValueError, match='non concluante'):
        source_spl_from_on_off(52., 50.)
    with pytest.raises(ValueError, match='invalide'):
        measured_emergence(source, 50., 0., .02)


def test_audibility_page_initial_and_nominal_comparison():
    page = Path(__file__).parent/'pages'/'1_Audibilite.py'
    at = AppTest.from_file(str(page), default_timeout=120).run()
    assert not at.exception
    assert any('niveau acoustique au public' in item.value.lower() for item in at.markdown)
    button = next(item for item in at.button if item.label == 'Calculer la comparaison 10 % / 22,5 %')
    at = button.click().run()
    assert not at.exception
    assert len(at.session_state.audibility_nominal) == 12


def test_audibility_page_measurement_and_variants():
    page = Path(__file__).parent/'pages'/'1_Audibilite.py'
    at = AppTest.from_file(str(page), default_timeout=120).run()
    at = next(item for item in at.button
              if item.label == 'Comparer les variantes de fixation et d’amortissement').click().run()
    assert not at.exception
    assert len(at.session_state.audibility_sensitivity) == 8
    at = next(item for item in at.checkbox
              if item.label == 'Je dispose de mesures acoustiques et d’une force d’excitation étalonnées').check().run()
    assert not at.exception
    assert any('Source estimée au micro' in item.label for item in at.metric)
