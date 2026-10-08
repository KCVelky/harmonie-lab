import io
import wave
from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from instrument_complet import (combined_sound, evaluate_instrument,
                                example_strings, make_strings, preview_audio,
                                summarize_instrument)
from rayonnement import evaluate_projection


def test_example_load_and_modes():
    wires, info = make_strings(example_strings())
    assert len(wires) == len(info) == 25
    assert 0 < sum(item['tension_n'] for item in info) / 9.80665 < 550
    assert all(item['frequency_hz'] > item['fundamental_hz'] for item in info)
    disabled = example_strings(2)
    disabled[0]['active'] = False
    wires, info = make_strings(disabled)
    assert not wires[0].active and info[0]['tension_n'] > 0


def test_one_string_agrees_with_existing_projection():
    record = example_strings(1)
    new, info = evaluate_instrument(record, orders=(8, 10),
                                    integration_points=24)
    old, _ = evaluate_projection(
        record[0]['length_m'], record[0]['fundamental_hz'],
        record[0]['magnet_pct'] / 100, .05, 500., .012,
        15., (5., 0., 1.6), orders=(8, 10),
        harmonics=(7,), integration_points=24)
    assert info[0]['frequency_hz'] == pytest.approx(old[0]['frequency_hz'])
    for current, previous in zip(new, old):
        assert current['pressure_rms_per_n'] == pytest.approx(
            previous['pressure_rms_per_n'], rel=1e-8)


def test_simultaneous_sources_respect_phase_and_force():
    row = dict(active=True, frequency_hz=60., force_peak_n=1.)
    row['complex_0.1'] = 1+0j
    opposite = dict(row)
    opposite['complex_0.1'] = -1+0j
    locked = combined_sound([row, opposite], .10, phase_locked=True)
    unlocked = combined_sound([row, opposite], .10, phase_locked=False)
    assert locked['pressure_rms_pa'] == 0
    assert unlocked['pressure_rms_pa'] == pytest.approx(1.)
    two_frequencies = combined_sound([row, dict(opposite, frequency_hz=61.)],
                                     .10, phase_locked=True)
    assert two_frequencies['pressure_rms_pa'] == pytest.approx(1.)


def test_preview_is_normalized_wav():
    row = dict(active=True, frequency_hz=60., force_peak_n=.01)
    row['complex_0.1'] = 1+2j
    payload = preview_audio([row], .10, duration_s=.5)
    with wave.open(io.BytesIO(payload), 'rb') as wav:
        assert wav.getnchannels() == 1
        assert wav.getframerate() == 8000
        samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype='<i2')
    assert len(samples) == 4000
    assert max(abs(samples)) > 1000


def test_instrument_page_initial_and_full_calculation():
    page = Path(__file__).parent / 'pages' / '3_Instrument_complet.py'
    app = AppTest.from_file(str(page), default_timeout=120).run()
    assert not app.exception
    button = next(item for item in app.button
                  if item.label == 'Calculer les 25 cordes et les deux chevalets')
    app = button.click().run()
    assert not app.exception
    assert len(app.session_state.instrument_result[0]) == 100
