"""Projection acoustique conditionnelle d'une table vibrante en écran rigide infini."""

from dataclasses import replace

import numpy as np
from numpy.polynomial.legendre import leggauss
from scipy.linalg import eigh
from scipy.sparse import diags

from audibilite import museum_case
from physics import assemble, basis, response, string_frequencies


AIR_DENSITY = 1.20
SOUND_SPEED = 343.0
REFERENCE_PRESSURE = 20e-6


def string_fem_tension_modes(length_m, tension_n, line_density_kg_m, elements, ranks):
    """Éléments linéaires 1D, masse cohérente, extrémités immobiles."""
    if (not all(np.isfinite((length_m, tension_n, line_density_kg_m)))
            or min(length_m, tension_n, line_density_kg_m) <= 0
            or elements < 3 or ranks < 1 or ranks >= elements):
        raise ValueError('Paramètres du contrôle éléments finis invalides.')
    element_length = length_m / elements
    nodes = elements - 1
    main_k = np.full(nodes, 2 * tension_n / element_length)
    side_k = np.full(nodes - 1, -tension_n / element_length)
    main_m = np.full(nodes, 2 * line_density_kg_m * element_length / 3)
    side_m = np.full(nodes - 1, line_density_kg_m * element_length / 6)
    stiffness = diags((side_k, main_k, side_k), (-1, 0, 1)).toarray()
    mass = diags((side_m, main_m, side_m), (-1, 0, 1)).toarray()
    values = eigh(stiffness, mass, subset_by_index=(0, ranks - 1),
                  eigvals_only=True)
    return np.sqrt(values) / (2 * np.pi)


def pressure_from_surface(displacement_peak_m, weights_m2, source_s_m,
                          source_u_m, frequency_hz, receiver_xyz_m,
                          center_height_m, plate_height_m, plate_width_m,
                          air_density=AIR_DENSITY, sound_speed=SOUND_SPEED):
    """Intégrale de Rayleigh sur la face avant, phasors en exp(+iωt)."""
    displacement = np.asarray(displacement_peak_m, dtype=complex)
    weights = np.asarray(weights_m2, dtype=float)
    source_s = np.asarray(source_s_m, dtype=float)
    source_u = np.asarray(source_u_m, dtype=float)
    receiver = np.asarray(receiver_xyz_m, dtype=float)
    if (displacement.shape != weights.shape or weights.shape != source_s.shape
            or weights.shape != source_u.shape or receiver.shape != (3,)
            or not np.all(np.isfinite(displacement))
            or not np.all(np.isfinite(weights))
            or not np.all(np.isfinite(source_s))
            or not np.all(np.isfinite(source_u))
            or not np.all(np.isfinite(receiver))
            or not np.isfinite(center_height_m)
            or not np.isfinite(plate_height_m) or plate_height_m <= 0
            or not np.isfinite(plate_width_m) or plate_width_m <= 0
            or frequency_hz <= 0 or air_density <= 0 or sound_speed <= 0
            or receiver[0] <= 0 or np.any(weights <= 0)):
        raise ValueError('Surface, fréquence ou point d’écoute invalide.')
    omega = 2 * np.pi * frequency_hz
    wavenumber = omega / sound_speed
    source_z = center_height_m + source_s - plate_height_m / 2
    source_y = source_u - plate_width_m / 2
    distance = np.sqrt(receiver[0] ** 2 + (receiver[1] - source_y) ** 2
                       + (receiver[2] - source_z) ** 2)
    integral = np.sum(weights * displacement
                      * np.exp(-1j * wavenumber * distance) / distance)
    return -air_density * omega ** 2 * integral / (2 * np.pi)


def acoustic_level(pressure_rms_pa):
    if not np.isfinite(pressure_rms_pa) or pressure_rms_pa < 0:
        raise ValueError('Pression acoustique invalide.')
    if pressure_rms_pa == 0:
        return float('-inf')
    return float(20 * np.log10(pressure_rms_pa / REFERENCE_PRESSURE))


def force_for_target_level(pressure_rms_per_n, target_spl_db):
    if (not np.isfinite(pressure_rms_per_n)
            or pressure_rms_per_n <= 0 or not np.isfinite(target_spl_db)):
        raise ValueError('Transfert ou niveau cible invalide.')
    return float(REFERENCE_PRESSURE * 10 ** (target_spl_db / 20)
                 / pressure_rms_per_n)


def evaluate_projection(length_m, fundamental_hz, magnet_fraction,
                        contact_fraction, coupling_n_m, plate_damping,
                        center_height_m, receiver_xyz_m, orders=(12, 14),
                        bridge_fractions=(.10, .225), harmonics=(5, 7),
                        integration_points=48, bridge_mass_kg=5.,
                        plate_modulus_gpa=10., plate_density_kg_m3=650.,
                        boundary='Appuis simples', support_enabled=True):
    """Transfert Pa RMS/N crête, par position et harmonique, sans salle."""
    if (len(orders) < 2 or any(not 3 <= order <= 14 for order in orders)
            or any(b <= a for a, b in zip(orders, orders[1:]))
            or integration_points < 20 or integration_points > 80
            or not np.isfinite(bridge_mass_kg) or bridge_mass_kg < 0
            or not np.isfinite(plate_modulus_gpa) or plate_modulus_gpa <= 0
            or not np.isfinite(plate_density_kg_m3)
            or plate_density_kg_m3 <= 0
            or boundary not in ('Appuis simples', 'Encastrement')
            or not all(0 < fraction < 1 for fraction in bridge_fractions)):
        raise ValueError('Résolution ou position de chevalet invalide.')
    plate, wire, support = museum_case(
        length_m, fundamental_hz, magnet_fraction, contact_fraction,
        coupling_n_m, 1., plate_damping)
    modulus = plate_modulus_gpa * 1e9
    plate = replace(plate, bridge_mass=bridge_mass_kg,
                    Es=modulus, Eu=modulus,
                    G=modulus / (2 * (1 + plate.nu)),
                    rho=plate_density_kg_m3, boundary=boundary)
    support = replace(support, enabled=support_enabled)
    if any(rank < 1 or rank > 12 for rank in harmonics):
        raise ValueError('Rang harmonique hors du modèle.')
    frequencies = string_frequencies(wire, max(harmonics))
    x, quadrature_weights = leggauss(integration_points)
    s_grid, u_grid = np.meshgrid((x + 1) * plate.H / 2,
                                 (x + 1) * plate.W / 2, indexing='ij')
    area_weights = np.outer(quadrature_weights, quadrature_weights).ravel()
    area_weights *= plate.H * plate.W / 4
    source_s = s_grid.ravel()
    source_u = u_grid.ravel()
    rows = []
    for order in orders:
        for bridge_fraction in bridge_fractions:
            case_plate = replace(plate, order=order,
                                 bridge_s=plate.H * (1 - bridge_fraction))
            model = assemble(case_plate, [wire], ns=12, support=support)
            shape = basis(case_plate, source_s, source_u)
            target_frequencies = [float(frequencies[rank - 1])
                                  for rank in harmonics]
            generalized = response(model, target_frequencies, 0)
            surface = shape @ generalized[:model['np'], :]
            for j, rank in enumerate(harmonics):
                complex_pressure = pressure_from_surface(
                    surface[:, j], area_weights, source_s, source_u,
                    target_frequencies[j], receiver_xyz_m, center_height_m,
                    plate.H, plate.W)
                rows.append(dict(order=order,
                                 bridge_top_fraction=bridge_fraction,
                                 harmonic=rank,
                                 frequency_hz=target_frequencies[j],
                                 pressure_rms_per_n=abs(complex_pressure)
                                 / np.sqrt(2),
                                 pressure_peak_complex_per_n=complex_pressure))
    return rows, wire


def summarize_projection(rows, tolerance=.10):
    orders = sorted({row['order'] for row in rows})
    positions = sorted({row['bridge_top_fraction'] for row in rows})
    harmonics = sorted({row['harmonic'] for row in rows})
    if len(orders) < 2 or len(positions) != 2:
        raise ValueError('Deux résolutions et deux positions sont nécessaires.')
    output = []
    for rank in harmonics:
        result = {'harmonic': rank}
        values = []
        for position in positions:
            group = {row['order']: row for row in rows
                     if row['harmonic'] == rank
                     and row['bridge_top_fraction'] == position}
            if set(group) != set(orders):
                raise ValueError('Comparaison incomplète.')
            changes = [abs(group[b]['pressure_rms_per_n']
                           - group[a]['pressure_rms_per_n'])
                       / max(group[a]['pressure_rms_per_n'],
                             group[b]['pressure_rms_per_n'], 1e-30)
                       for a, b in zip(orders, orders[1:])]
            latest = group[orders[-1]]
            values.append(latest['pressure_rms_per_n'])
            result[f'pressure_{position:g}'] = latest['pressure_rms_per_n']
            result[f'convergence_{position:g}'] = max(changes)
        result['frequency_hz'] = group[orders[-1]]['frequency_hz']
        result['ratio_first_over_second'] = values[0] / max(values[1], 1e-30)
        result['stable'] = all(result[f'convergence_{position:g}'] <= tolerance
                               for position in positions)
        output.append(result)
    return output
