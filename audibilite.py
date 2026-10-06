"""Comparaisons traçables pour l'étude d'audibilité d'une corde longue."""

from dataclasses import replace

import numpy as np

from etude_sandra import compare_positions, reference_string, summarize_comparison
from physics import Plate, Support, tension_for


def museum_case(length_m=10., fundamental_hz=12., magnet_fraction=.10,
                contact_fraction=.05, coupling_n_m=500., force_peak_n=.01,
                plate_damping=.012):
    plate = Plate(H=2.4384, W=1.524, h=.003175, rho=650., Es=10e9,
                  Eu=10e9, G=10e9/2.6, nu=.30, boundary='Appuis simples',
                  bridge_s=2.19456, bridge_mass=.010, damping=plate_damping,
                  order=10)
    support = Support(enabled=True, width=.0381, depth=.0381,
                      rho=500., E=10e9)
    base = replace(reference_string(), L=length_m, p1=magnet_fraction,
                   beta=contact_fraction, coupling=coupling_n_m,
                   force=force_peak_n)
    wire = replace(base, T=tension_for(base, fundamental_hz, 1))
    return plate, wire, support


def geometry_factors(harmonic, magnet_fraction, contact_fraction):
    """Projections modales de la corde isolée, sans prédiction de rendement."""
    if harmonic < 1 or not all(0 < x < 1 for x in (magnet_fraction, contact_fraction)):
        raise ValueError('Harmonique ou position hors domaine.')
    return (abs(np.sin(np.pi*harmonic*magnet_fraction)),
            abs(np.sin(np.pi*harmonic*contact_fraction)))


def band_energy(spectral_result, center_hz, half_width_hz=1.):
    """Variance du signal WAV dans une bande, en unités numériques au carré."""
    frequency = np.asarray(spectral_result['frequency_hz'], dtype=float)
    density = np.asarray(spectral_result['power'], dtype=float)
    if (frequency.ndim != 1 or density.shape != frequency.shape or len(frequency) < 2
            or not np.all(np.isfinite(frequency)) or not np.all(np.isfinite(density))
            or np.any(density < 0) or not np.all(np.diff(frequency) > 0)
            or center_hz <= 0 or half_width_hz <= 0):
        raise ValueError('Spectre ou bande invalide.')
    selected = abs(frequency-center_hz) <= half_width_hz
    if not np.any(selected):
        raise ValueError('Aucun point spectral dans la bande.')
    widths = np.diff(frequency)
    if not np.allclose(widths, widths[0], rtol=1e-5):
        raise ValueError('La grille fréquentielle doit être régulière.')
    return float(np.sum(density[selected])*widths[0])


def weighted_mechanical_index(summary, energies, filter_gains_db=None):
    """Indice comparatif : forces supposées proportionnelles au signal filtré."""
    if any(not row['stable'] for row in summary):
        raise ValueError('Convergence mécanique insuffisante.')
    gains = filter_gains_db or {}
    weights = {}
    for row in summary:
        harmonic = row['harmonic']
        energy = float(energies[harmonic])
        gain = float(gains.get(harmonic, 0.))
        if not np.isfinite(energy) or energy < 0 or not np.isfinite(gain):
            raise ValueError('Poids spectral ou gain invalide.')
        weights[harmonic] = energy*10**(gain/10)
    total = sum(weights.values())
    if total <= 0:
        raise ValueError('Énergie nulle dans les bandes sélectionnées.')
    return {
        '10 %': float(np.sqrt(sum(weights[row['harmonic']]*row['rms_10']**2
                               for row in summary)/total)),
        '22,5 %': float(np.sqrt(sum(weights[row['harmonic']]*row['rms_22_5']**2
                                 for row in summary)/total)),
    }


def comparison_variants(plate, wire, support):
    """Variantes structurales, chacune avec contrôle de convergence."""
    cases = (
        ('Référence', plate, support),
        ('Sans traverse', plate, replace(support, enabled=False)),
        ('Bords encastrés', replace(plate, boundary='Encastrement'), support),
        ('Amortissement doublé', replace(plate, damping=2*plate.damping), support),
    )
    result = []
    for name, case_plate, case_support in cases:
        rows = compare_positions(case_plate, wire, case_support, orders=(12, 14))
        for item in summarize_comparison(rows):
            result.append(dict(case=name, **item))
    return result


def measured_emergence(source_spl_db, ambient_band_spl_db,
                       reference_force_peak_n, planned_force_peak_n,
                       uncertainty_db=0.):
    """Extrapolation linéaire d'une mesure acoustique isolée de la source."""
    values = (source_spl_db, ambient_band_spl_db, reference_force_peak_n,
              planned_force_peak_n, uncertainty_db)
    if not all(np.isfinite(values)) or min(reference_force_peak_n, planned_force_peak_n) <= 0 or uncertainty_db < 0:
        raise ValueError('Mesure, force ou incertitude invalide.')
    projected = source_spl_db + 20*np.log10(planned_force_peak_n/reference_force_peak_n)
    margin = projected-ambient_band_spl_db
    return dict(projected_source_spl_db=float(projected),
                margin_db=float(margin), conservative_margin_db=float(margin-uncertainty_db))


def source_spl_from_on_off(on_band_spl_db, off_band_spl_db):
    """Soustraction énergétique de deux niveaux RMS mesurés dans la même bande."""
    if not np.isfinite(on_band_spl_db) or not np.isfinite(off_band_spl_db):
        raise ValueError('Niveaux acoustiques invalides.')
    difference = on_band_spl_db-off_band_spl_db
    if difference < 3.:
        raise ValueError('Écart marche/arrêt inférieur à 3 dB : extraction non concluante.')
    return float(on_band_spl_db+10*np.log10(1-10**(-difference/10)))
