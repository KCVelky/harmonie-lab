"""Étude harmonique de plusieurs cordes couplées à une table verticale."""

from dataclasses import replace
import io
import wave

import numpy as np
from numpy.polynomial.legendre import leggauss
from threadpoolctl import threadpool_limits

from audibilite import museum_case
from physics import assemble, basis, response, string_frequencies, tension_for
from rayonnement import acoustic_level, pressure_from_surface
from rayonnement_spectral import build_spectral_system, spectral_pressure


def example_strings(count=25):
    """Jeu de départ illustratif, sans prétendre décrire les accords définitifs."""
    if not 1 <= count <= 25:
        raise ValueError('Le nombre de cordes doit être compris entre 1 et 25.')
    lengths = np.linspace(7.45, 11.55, count)
    fundamentals = np.linspace(12., 9., count)
    return [dict(number=i + 1, active=True, length_m=float(length),
                 fundamental_hz=float(fundamental), harmonic=7,
                 magnet_pct=100 / 14, force_peak_n=.01)
            for i, (length, fundamental) in enumerate(zip(lengths, fundamentals))]


def make_strings(records, contact_fraction=.05, coupling_n_m=500.):
    if not records or len(records) > 25:
        raise ValueError('Le scénario doit contenir entre 1 et 25 cordes.')
    _, template, _ = museum_case()
    output = []
    info = []
    for index, row in enumerate(records):
        try:
            length = float(row['length_m'])
            fundamental = float(row['fundamental_hz'])
            harmonic = int(row['harmonic'])
            magnet_fraction = float(row['magnet_pct']) / 100
            force = float(row['force_peak_n'])
            active = bool(row['active'])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f'Corde {index + 1} : cellule manquante ou invalide.') from exc
        if (not np.all(np.isfinite([length, fundamental, magnet_fraction, force]))
                or not 7.45 <= length <= 11.55 or not 7 <= fundamental <= 20
                or not 1 <= harmonic <= 8 or not .01 <= magnet_fraction <= .99
                or force < 0 or force > 10 or not 0 < contact_fraction < 1
                or coupling_n_m < 0):
            raise ValueError(f'Corde {index + 1} : valeur hors limites du modèle.')
        wire = replace(template, L=length, T=1., p1=magnet_fraction,
                       p2=.5, gain2=0., force=1., active=active,
                       beta=contact_fraction, coupling=coupling_n_m,
                       u=(index + 1) / (len(records) + 1))
        tension = tension_for(wire, fundamental)
        if tension <= 0:
            raise ValueError(f'Corde {index + 1} : tension calculée non positive.')
        wire = replace(wire, T=tension)
        frequency = float(string_frequencies(wire, harmonic)[harmonic - 1])
        output.append(wire)
        info.append(dict(number=index + 1, active=active, length_m=length,
                         fundamental_hz=fundamental, harmonic=harmonic,
                         frequency_hz=frequency, tension_n=tension,
                         force_peak_n=force, magnet_pct=100 * magnet_fraction,
                         magnet_projection=abs(np.sin(np.pi * harmonic * magnet_fraction)),
                         bridge_projection=abs(np.sin(np.pi * harmonic * contact_fraction))))
    return output, info


def evaluate_instrument(records, *, contact_fraction=.05, coupling_n_m=500.,
                        damping=.012, bridge_mass_kg=5., modulus_gpa=10.,
                        density_kg_m3=650., boundary='Appuis simples',
                        support_enabled=True, center_height_m=15.,
                        receiver_xyz_m=(5., 0., 1.6), orders=(10, 12),
                        positions=(.10, .225), integration_points=28):
    """Transferts complexes Pa crête/N crête, avec toutes les cordes couplées."""
    wires, string_info = make_strings(records, contact_fraction, coupling_n_m)
    if (len(orders) != 2 or not 3 <= orders[0] < orders[1] <= 14
            or integration_points < 20 or integration_points > 60
            or len(positions) != 2 or any(not 0 < x < 1 for x in positions)
            or not .0001 <= damping <= .3 or bridge_mass_kg < 0
            or modulus_gpa <= 0 or density_kg_m3 <= 0
            or boundary not in ('Appuis simples', 'Encastrement')):
        raise ValueError('Hypothèse structurelle ou résolution invalide.')
    plate, _, support = museum_case()
    modulus = modulus_gpa * 1e9
    plate = replace(plate, bridge_mass=bridge_mass_kg, Es=modulus, Eu=modulus,
                    G=modulus / (2 * (1 + plate.nu)), rho=density_kg_m3,
                    boundary=boundary, damping=damping)
    support = replace(support, enabled=support_enabled)
    nodes, weights = leggauss(integration_points)
    s_grid, u_grid = np.meshgrid((nodes + 1) * plate.H / 2,
                                 (nodes + 1) * plate.W / 2, indexing='ij')
    source_s = s_grid.ravel()
    source_u = u_grid.ravel()
    area_weights = (np.outer(weights, weights) * plate.H * plate.W / 4).ravel()
    results = []
    for order in orders:
        for position in positions:
            case_plate = replace(plate, order=order,
                                 bridge_s=plate.H * (1 - position))
            model = assemble(case_plate, wires, ns=12, support=support)
            shape = basis(case_plate, source_s, source_u)
            for index, item in enumerate(string_info):
                if not item['active']:
                    pressure = 0j
                else:
                    displacement = response(model, [item['frequency_hz']], index)
                    surface = shape @ displacement[:model['np'], 0]
                    pressure = pressure_from_surface(
                        surface, area_weights, source_s, source_u,
                        item['frequency_hz'], receiver_xyz_m, center_height_m,
                        plate.H, plate.W)
                results.append(dict(order=order, bridge_top_fraction=position,
                                    number=index + 1, pressure_peak_per_n=pressure,
                                    pressure_rms_per_n=abs(pressure) / np.sqrt(2)))
    return results, string_info


@threadpool_limits.wrap(limits=1, user_api='blas')
def evaluate_instrument_spectral(records, *, contact_fraction=.05,
                                 coupling_n_m=500., damping=.012,
                                 bridge_mass_kg=5., modulus_gpa=10.,
                                 density_kg_m3=650., boundary='Appuis simples',
                                 support_enabled=True, center_height_m=15.,
                                 receiver_xyz_m=(5., 0., 1.6),
                                 orders=(20, 24), positions=(.10, .225),
                                 integration_points=28):
    """Réponse directe à haute résolution, avec amortissement structurel."""
    wires, string_info = make_strings(records, contact_fraction, coupling_n_m)
    if (len(orders) < 2 or any(not 4 <= order <= 50 for order in orders)
            or any(right <= left for left, right in zip(orders, orders[1:]))
            or len(positions) != 2 or any(not 0 < x < 1 for x in positions)
            or not .0001 <= damping <= .3 or bridge_mass_kg < 0
            or modulus_gpa <= 0 or density_kg_m3 <= 0
            or boundary != 'Appuis simples'):
        raise ValueError('Le calcul spectral exige des appuis simples et des paramètres valides.')
    plate, _, support = museum_case()
    modulus = modulus_gpa * 1e9
    plate = replace(plate, bridge_mass=bridge_mass_kg, Es=modulus, Eu=modulus,
                    G=modulus / (2 * (1 + plate.nu)), rho=density_kg_m3,
                    boundary=boundary, damping=damping)
    support = replace(support, enabled=support_enabled)
    rows = []
    for order in orders:
        for position in positions:
            case_plate = replace(plate, bridge_s=plate.H * (1 - position))
            system = build_spectral_system(
                case_plate, wires, support, order=order,
                center_height=center_height_m, receiver=receiver_xyz_m,
                integration_points=integration_points)
            for index, item in enumerate(string_info):
                pressure = (spectral_pressure(system, wires[index], index,
                                              item['frequency_hz'])
                            if item['active'] else 0j)
                rows.append(dict(order=order, bridge_top_fraction=position,
                                 number=index + 1, pressure_peak_per_n=pressure,
                                 pressure_rms_per_n=abs(pressure) / np.sqrt(2)))
    return rows, string_info


def summarize_instrument(results, string_info, tolerance=.10):
    orders = sorted({item['order'] for item in results})
    positions = sorted({item['bridge_top_fraction'] for item in results})
    if len(orders) < 2 or len(positions) != 2:
        raise ValueError('Au moins deux résolutions et deux positions sont nécessaires.')
    lookup = {(item['number'], item['order'], item['bridge_top_fraction']): item
              for item in results}
    rows = []
    for item in string_info:
        row = dict(item)
        changes = []
        for position in positions:
            series = [lookup[(item['number'], order, position)]
                      for order in orders]
            magnitudes = [entry['pressure_rms_per_n'] for entry in series]
            change = ((max(magnitudes) - min(magnitudes))
                      / max(max(magnitudes), 1e-30))
            current = series[-1]
            row[f'pressure_{position:g}'] = current['pressure_rms_per_n']
            row[f'complex_{position:g}'] = current['pressure_peak_per_n']
            row[f'convergence_{position:g}'] = change
            changes.append(change)
        row['stable'] = not item['active'] or max(changes) <= tolerance
        rows.append(row)
    return rows


def combined_sound(rows, position, *, phase_locked=True):
    """Puissance moyenne des tons; somme complexe seulement à fréquence égale."""
    groups = []
    for row in rows:
        if not row['active'] or row['force_peak_n'] == 0:
            continue
        frequency = row['frequency_hz']
        pressure_peak = row[f'complex_{position:g}'] * row['force_peak_n']
        group = next((entry for entry in groups
                      if abs(entry['frequency_hz'] - frequency) < 1e-6), None)
        if group is None:
            group = dict(frequency_hz=frequency, peaks=[])
            groups.append(group)
        group['peaks'].append(pressure_peak)
    power = 0.
    lines = []
    for group in groups:
        peaks = np.asarray(group['peaks'])
        line_power = (abs(np.sum(peaks)) ** 2 if phase_locked
                      else float(np.sum(abs(peaks) ** 2))) / 2
        power += line_power
        lines.append(dict(frequency_hz=group['frequency_hz'],
                          contributors=len(peaks), pressure_rms_pa=float(np.sqrt(line_power)),
                          level_db_spl=acoustic_level(float(np.sqrt(line_power)))))
    return dict(pressure_rms_pa=float(np.sqrt(power)),
                level_db_spl=acoustic_level(float(np.sqrt(power))), lines=lines)


def collective_convergence(results, string_info, *, phase_locked=False):
    """Convergence du niveau collectif, distincte de chaque transfert individuel."""
    orders = sorted({item['order'] for item in results})
    positions = sorted({item['bridge_top_fraction'] for item in results})
    if len(orders) < 2:
        raise ValueError('Deux résolutions sont nécessaires.')
    output = {}
    for position in positions:
        pressures = []
        for order in orders:
            rows = []
            for raw in results:
                if raw['order'] != order or raw['bridge_top_fraction'] != position:
                    continue
                item = string_info[raw['number'] - 1]
                rows.append(dict(item, **{f'complex_{position:g}': raw['pressure_peak_per_n']}))
            sound = combined_sound(rows, position, phase_locked=phase_locked)
            pressures.append(sound['pressure_rms_pa'])
        span = (max(pressures) - min(pressures)) / max(max(pressures), 1e-30)
        output[position] = dict(orders=orders, pressure_rms_pa=pressures,
                                relative_span=span,
                                latest_level_db_spl=acoustic_level(pressures[-1]))
    return output


def preview_audio(rows, position, duration_s=5., sample_rate=8000):
    """Préécoute normalisée des pressions harmoniques, sans volume absolu."""
    if not 0 < duration_s <= 12 or sample_rate < 1000:
        raise ValueError('Durée ou fréquence audio invalide.')
    time = np.arange(int(duration_s * sample_rate)) / sample_rate
    signal = np.zeros(len(time), dtype=float)
    for row in rows:
        if not row['active'] or row['force_peak_n'] <= 0:
            continue
        frequency = row['frequency_hz']
        if frequency >= sample_rate / 2:
            raise ValueError('Fréquence sonore supérieure à la limite audio.')
        pressure = row[f'complex_{position:g}'] * row['force_peak_n']
        signal += (pressure.real * np.cos(2 * np.pi * frequency * time)
                   - pressure.imag * np.sin(2 * np.pi * frequency * time))
    peak = np.max(abs(signal))
    if peak == 0:
        raise ValueError('Aucune corde active avec une force non nulle.')
    fade = min(int(.04 * sample_rate), len(signal) // 4)
    envelope = np.ones(len(signal))
    envelope[:fade] = np.linspace(0, 1, fade)
    envelope[-fade:] = np.linspace(1, 0, fade)
    pcm = np.round(signal / peak * envelope * 0.9 * 32767).astype('<i2')
    output = io.BytesIO()
    with wave.open(output, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm.tobytes())
    return output.getvalue()
