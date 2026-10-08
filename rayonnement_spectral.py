"""Réponse harmonique haute résolution d'une table à appuis simples."""

from dataclasses import dataclass

import numpy as np
from numpy.polynomial.legendre import leggauss
from scipy.linalg import solve

from physics import string_frequencies
from rayonnement import pressure_from_surface


@dataclass
class SpectralSystem:
    order: int
    plate_dofs: int
    diagonal_mass: np.ndarray
    diagonal_stiffness: np.ndarray
    loss_factor: np.ndarray
    updates: np.ndarray
    update_stiffness: np.ndarray
    update_mass: np.ndarray
    update_loss_factor: np.ndarray
    surface_basis: np.ndarray
    source_s: np.ndarray
    source_u: np.ndarray
    area_weights: np.ndarray
    plate_height: float
    plate_width: float
    center_height: float
    receiver: tuple
    wire_count: int
    string_modes: int


def build_spectral_system(plate, wires, support, *, order,
                          center_height, receiver, integration_points=28,
                          string_modes=12):
    """Matrice dynamique diagonale et corrections de faible rang exactes."""
    if (plate.boundary != 'Appuis simples' or plate.angle != 0
            or not np.isclose(plate.Es, plate.Eu)
            or not np.isclose(plate.G, plate.Es / (2 * (1 + plate.nu)))
            or not 4 <= order <= 50 or not 20 <= integration_points <= 60
            or not 1 <= string_modes <= 20):
        raise ValueError('Le solveur spectral exige une plaque isotrope à appuis simples.')
    n = np.arange(1, order + 1)
    ks = n * np.pi / plate.H
    ku = n * np.pi / plate.W
    ks_grid, ku_grid = np.meshgrid(ks, ku, indexing='ij')
    plate_dofs = order ** 2
    wire_count = len(wires)
    total_dofs = plate_dofs + wire_count * string_modes
    flexural_rigidity = plate.Es * plate.h ** 3 / (12 * (1 - plate.nu ** 2))
    diagonal_mass = np.empty(total_dofs)
    diagonal_stiffness = np.empty(total_dofs)
    loss_factor = np.empty(total_dofs)
    diagonal_mass[:plate_dofs] = plate.rho * plate.h * plate.H * plate.W / 4
    diagonal_stiffness[:plate_dofs] = (
        flexural_rigidity * plate.H * plate.W / 4
        * (ks_grid ** 2 + ku_grid ** 2).ravel() ** 2)
    loss_factor[:plate_dofs] = 2 * plate.damping
    for index, wire in enumerate(wires):
        start = plate_dofs + index * string_modes
        stop = start + string_modes
        mass = wire.rho * np.pi * wire.d ** 2 / 4 * wire.L / 2
        frequencies = string_frequencies(wire, string_modes)
        diagonal_mass[start:stop] = mass
        diagonal_stiffness[start:stop] = mass * (2 * np.pi * frequencies) ** 2
        loss_factor[start:stop] = 2 * wire.damping

    columns = []
    update_stiffness = []
    update_mass = []
    update_loss_factor = []
    if support.enabled:
        area = support.width * support.depth
        inertia = support.width * support.depth ** 3 / 12
        across = np.sin(n * np.pi * support.joint_u)
        for j, longitudinal_wavenumber in enumerate(ks):
            column = np.zeros(total_dofs)
            column[j * order:(j + 1) * order] = across
            columns.append(column)
            update_stiffness.append(support.E * inertia
                                    * longitudinal_wavenumber ** 4 * plate.H / 2)
            update_mass.append(support.rho * area * plate.H / 2)
            update_loss_factor.append(2 * plate.damping)
    if plate.bridge_mass > 0:
        along = np.sin(ks * plate.bridge_s)
        for j in range(order):
            column = np.zeros(total_dofs)
            column[np.arange(order) * order + j] = along
            columns.append(column)
            update_stiffness.append(0.)
            update_mass.append(plate.bridge_mass / 2)
            update_loss_factor.append(0.)
    for index, wire in enumerate(wires):
        if wire.coupling <= 0:
            continue
        column = np.zeros(total_dofs)
        longitudinal = np.sin(ks * plate.bridge_s)
        transverse = np.sin(ku * wire.u * plate.W)
        column[:plate_dofs] = -np.outer(longitudinal, transverse).ravel()
        start = plate_dofs + index * string_modes
        column[start:start + string_modes] = np.sin(
            np.arange(1, string_modes + 1) * np.pi * wire.beta)
        columns.append(column)
        update_stiffness.append(wire.coupling)
        update_mass.append(0.)
        update_loss_factor.append(0.)
    updates = (np.column_stack(columns) if columns
               else np.zeros((total_dofs, 0)))

    nodes, weights = leggauss(integration_points)
    source_s, source_u = np.meshgrid((nodes + 1) * plate.H / 2,
                                     (nodes + 1) * plate.W / 2,
                                     indexing='ij')
    source_s = source_s.ravel()
    source_u = source_u.ravel()
    longitudinal = np.sin(source_s[:, None] * ks)
    transverse = np.sin(source_u[:, None] * ku)
    surface_basis = (longitudinal[:, :, None]
                     * transverse[:, None, :]).reshape(-1, plate_dofs)
    area_weights = (np.outer(weights, weights)
                    * plate.H * plate.W / 4).ravel()
    return SpectralSystem(
        order, plate_dofs, diagonal_mass, diagonal_stiffness, loss_factor,
        updates, np.asarray(update_stiffness), np.asarray(update_mass),
        np.asarray(update_loss_factor), surface_basis, source_s, source_u,
        area_weights, plate.H, plate.W, center_height, tuple(receiver),
        wire_count, string_modes)


def dynamic_displacement(system, frequency_hz, force_vector):
    """Formule de Woodbury pour la réponse complexe à fréquence imposée."""
    omega = 2 * np.pi * frequency_hz
    diagonal = (system.diagonal_stiffness * (1 + 1j * system.loss_factor)
                - omega ** 2 * system.diagonal_mass)
    direct = np.asarray(force_vector, dtype=complex) / diagonal
    if system.updates.shape[1] == 0:
        return direct
    coefficients = (system.update_stiffness
                    * (1 + 1j * system.update_loss_factor)
                    - omega ** 2 * system.update_mass)
    inverse_updates = system.updates / diagonal[:, None]
    interaction = system.updates.T @ inverse_updates
    small_matrix = (np.eye(len(coefficients), dtype=complex)
                    + coefficients[:, None] * interaction)
    rhs = coefficients * (system.updates.T @ direct)
    correction = solve(small_matrix, rhs, assume_a='gen', check_finite=False)
    return direct - inverse_updates @ correction


def spectral_pressure(system, wire, wire_index, frequency_hz):
    force = np.zeros(len(system.diagonal_mass))
    start = system.plate_dofs + wire_index * system.string_modes
    ranks = np.arange(1, system.string_modes + 1)
    force[start:start + system.string_modes] = np.sin(ranks * np.pi * wire.p1)
    displacement = dynamic_displacement(system, frequency_hz, force)
    surface = system.surface_basis @ displacement[:system.plate_dofs]
    return pressure_from_surface(
        surface, system.area_weights, system.source_s, system.source_u,
        frequency_hz, system.receiver, system.center_height,
        system.plate_height, system.plate_width)
