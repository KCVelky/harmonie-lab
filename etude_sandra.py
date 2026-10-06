"""Comparaison mécanique à une corde pour deux positions du chevalet."""
from dataclasses import replace

import numpy as np

from physics import (String, assemble, basis, quadrature, response,
                     string_frequencies, tension_for)


POSITIONS = (0.10, 0.225)
HARMONICS = (5, 7)


def reference_string():
    wire = String(L=10., d=.000762, u=.5, beta=.05, coupling=500.,
                  force=.01, p1=.10, p2=.90, gain2=0.)
    wire = replace(wire, T=tension_for(wire, 12., 1))
    return replace(wire, drive=string_frequencies(wire, 5)[-1])


def plate_metrics(model, frequency, string_index=0):
    p = model['p']
    s, u, weights = quadrature(p)
    displacement = basis(p, s, u) @ response(model, [frequency], string_index)[:model['np'], 0]
    scale = (2*np.pi*frequency)**2
    rms = scale*np.sqrt(np.sum(weights*np.abs(displacement)**2)/np.sum(weights))
    coherent = scale*np.abs(np.sum(weights*displacement)/np.sum(weights))
    return float(rms), float(coherent)


def compare_positions(plate, wire, support, orders=(10, 12, 14), ns=12):
    if len(orders)<2 or any(b<=a for a,b in zip(orders, orders[1:])):
        raise ValueError('Prévoir au moins deux résolutions croissantes.')
    if ns < max(HARMONICS):
        raise ValueError('Le nombre de modes de corde est insuffisant.')
    targets = {rank: float(string_frequencies(wire, rank)[-1]) for rank in HARMONICS}
    rows = []
    for order in orders:
        for top_fraction in POSITIONS:
            candidate = replace(plate, order=order,
                                bridge_s=plate.H*(1-top_fraction))
            model = assemble(candidate, [wire], ns, support)
            for rank, frequency in targets.items():
                rms, coherent = plate_metrics(model, frequency)
                rows.append(dict(order=order, bridge_top_pct=top_fraction*100,
                                 harmonic=rank, force_hz=frequency,
                                 rms_acceleration=rms,
                                 coherent_acceleration=coherent))
    return rows


def summarize_comparison(rows, threshold=.10):
    orders = sorted({int(r['order']) for r in rows})
    if len(orders)<2:
        raise ValueError('Deux résolutions sont nécessaires pour conclure.')
    result = []
    for rank in HARMONICS:
        pair = []
        for top_fraction in POSITIONS:
            subset = {int(r['order']): r for r in rows
                      if r['harmonic']==rank and abs(r['bridge_top_pct']-100*top_fraction)<1e-8}
            latest = subset[orders[-1]]
            changes = {}
            for key in ('rms_acceleration','coherent_acceleration'):
                changes[key] = max(
                    abs(subset[high][key]-subset[low][key])
                    / max(subset[high][key],subset[low][key],1e-30)
                    for low,high in zip(orders,orders[1:]))
            pair.append((latest, changes))
        left, right = pair
        ratio = left[0]['rms_acceleration']/max(right[0]['rms_acceleration'],1e-30)
        coherent_ratio = left[0]['coherent_acceleration']/max(right[0]['coherent_acceleration'],1e-30)
        stable = all(change['rms_acceleration']<=threshold for _,change in pair)
        coherent_stable = all(change['coherent_acceleration']<=threshold for _,change in pair)
        if not stable:
            verdict = 'Convergence insuffisante'
        elif ratio>=1.15:
            verdict = '10 % plus élevé dans le modèle'
        elif ratio<=1/1.15:
            verdict = '22,5 % plus élevé dans le modèle'
        else:
            verdict = 'Réponses proches dans le modèle'
        result.append(dict(harmonic=rank, force_hz=left[0]['force_hz'],
                           rms_10=left[0]['rms_acceleration'],
                           rms_22_5=right[0]['rms_acceleration'],
                           coherent_10=left[0]['coherent_acceleration'],
                           coherent_22_5=right[0]['coherent_acceleration'],
                           ratio_10_over_22_5=ratio,
                           coherent_ratio_10_over_22_5=coherent_ratio,
                           convergence_10=left[1]['rms_acceleration'],
                           convergence_22_5=right[1]['rms_acceleration'],
                           coherent_convergence_10=left[1]['coherent_acceleration'],
                           coherent_convergence_22_5=right[1]['coherent_acceleration'],
                           stable=stable, coherent_stable=coherent_stable,
                           verdict=verdict))
    return result
