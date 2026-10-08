import numpy as np
import pytest

from rayonnement import (REFERENCE_PRESSURE, acoustic_level,
                         evaluate_projection, force_for_target_level,
                         pressure_from_surface, string_fem_tension_modes,
                         summarize_projection)


def test_rayleigh_integral_matches_distant_uniform_piston():
    area = 2.0
    displacement = 1e-6
    frequency = 80.0
    distance = 1000.0
    pressure = pressure_from_surface(
        np.full(4, displacement), np.full(4, area / 4),
        np.array([0.2, 0.2, 0.8, 0.8]),
        np.array([0.2, 0.8, 0.2, 0.8]),
        frequency, (distance, 0.0, 0.0), 0.5, 1.0, 1.0)
    expected = 1.2 * (2 * np.pi * frequency) ** 2 * area * displacement
    expected /= 2 * np.pi * distance
    assert abs(pressure) == pytest.approx(expected, rel=1e-6)


def test_radiation_preserves_coherent_cancellation():
    pressure = pressure_from_surface(
        np.array([1e-6, -1e-6]), np.array([.5, .5]),
        np.array([.5, .5]), np.array([.25, .75]),
        60., (5., 0., 1.6), 1.6, 1., 1.)
    assert abs(pressure) < 1e-15


def test_string_finite_elements_converge_to_tension_formula():
    length, tension, line_density = 10., 206., .00358
    exact = np.arange(1, 8) / (2 * length) * np.sqrt(tension / line_density)
    coarse = string_fem_tension_modes(length, tension, line_density, 48, 7)
    fine = string_fem_tension_modes(length, tension, line_density, 96, 7)
    assert np.max(abs(fine - exact)) < np.max(abs(coarse - exact))
    assert np.max(abs(fine / exact - 1)) < .003


def test_level_and_required_force_are_inverse():
    transfer = .002
    level = acoustic_level(transfer * .01)
    force = force_for_target_level(transfer, level)
    assert force == pytest.approx(.01)
    assert acoustic_level(REFERENCE_PRESSURE) == pytest.approx(0.)


def test_projection_computes_two_positions_with_convergence():
    rows, wire = evaluate_projection(10., 12., .10, .05, 500., .012,
                                      15., (5., 0., 1.6),
                                      orders=(8, 10), integration_points=24)
    summary = summarize_projection(rows)
    assert wire.T > 0
    assert len(rows) == 8
    assert [r['harmonic'] for r in summary] == [5, 7]
    assert all(r['pressure_0.1'] > 0 and r['pressure_0.225'] > 0
               for r in summary)
    assert all(np.isfinite(r['ratio_first_over_second']) for r in summary)


def test_receiver_must_be_in_front_half_space():
    with pytest.raises(ValueError):
        pressure_from_surface(np.array([1e-6]), np.array([1.]),
                              np.array([.5]), np.array([.5]), 60.,
                              (0., 0., 1.), 1., 1., 1.)
