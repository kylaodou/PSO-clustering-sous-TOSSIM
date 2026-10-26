"""
PSO-clustering (Latiff et al., PIMRC 2007) : chaque particule est un score
d'aptitude par noeud ; les k meilleurs scores deviennent CH, fitness =
0.7*distance_intra_normalisee + 0.3*(1 - energie_CH/energie_max).
"""

from dataclasses import dataclass
import time
import numpy as np

from network import Node, BS_X, BS_Y, FIELD_X, FIELD_Y

W1_DIST = 0.7
W2_ENERGY = 0.3
P_OPT = 0.05          # proportion de Cluster Heads (valeur standard LEACH)
SWARM_SIZE = 20
ITERATIONS = 25
INERTIA_START = 0.9
INERTIA_END = 0.4
C1 = 1.49445
C2 = 1.49445
V_MAX = 0.2

FIELD_DIAG = float(np.hypot(FIELD_X, FIELD_Y))


@dataclass
class PSOResult:
    ch_ids: list          # ids des noeuds elus Cluster Head
    assignment: dict       # node_id -> ch_id (CH -> lui-meme)
    best_fitness: float
    iterations_run: int
    swarm_size: int
    dimension: int
    wall_clock_s: float
    evaluations: int


def run_pso(nodes: list[Node], seed: int | None = None,
            p_opt: float = P_OPT, swarm_size: int = SWARM_SIZE,
            iterations: int = ITERATIONS) -> PSOResult:
    t_start = time.perf_counter()
    rng = np.random.default_rng(seed)

    alive = nodes
    n = len(alive)
    if n == 0:
        raise ValueError("Aucun noeud vivant : impossible d'executer PSO")

    k = max(1, round(p_opt * n))
    k = min(k, n)

    xs = np.array([nd.x for nd in alive])
    ys = np.array([nd.y for nd in alive])
    energies = np.array([max(nd.energy, 1e-12) for nd in alive])
    e_max = float(energies.max())

    # matrice des distances euclidiennes noeud-noeud (n x n)
    dx = xs[:, None] - xs[None, :]
    dy = ys[:, None] - ys[None, :]
    dist_matrix = np.hypot(dx, dy)

    # --- initialisation de l'essaim ---
    positions = rng.uniform(0.0, 1.0, size=(swarm_size, n))
    velocities = rng.uniform(-V_MAX, V_MAX, size=(swarm_size, n))
    pbest_pos = positions.copy()
    pbest_fit = np.full(swarm_size, np.inf)
    gbest_pos = positions[0].copy()
    gbest_fit = np.inf
    evaluations = 0

    def decode_and_evaluate(pos_vec: np.ndarray):
        ch_local_idx = np.argpartition(-pos_vec, k - 1)[:k]
        sub_dist = dist_matrix[:, ch_local_idx]          # (n, k)
        nearest_ch_pos = np.argmin(sub_dist, axis=1)     # index dans ch_local_idx
        nearest_dist = sub_dist[np.arange(n), nearest_ch_pos]
        # les CH eux-memes ont une distance nulle a leur propre cluster
        non_ch_mask = np.ones(n, dtype=bool)
        non_ch_mask[ch_local_idx] = False
        if non_ch_mask.any():
            f1 = float(nearest_dist[non_ch_mask].mean()) / FIELD_DIAG
        else:
            f1 = 0.0
        ch_energy_mean = float(energies[ch_local_idx].mean())
        f2 = 1.0 - (ch_energy_mean / e_max)
        fitness = W1_DIST * f1 + W2_ENERGY * f2
        return fitness, ch_local_idx, nearest_ch_pos

    for i in range(swarm_size):
        fit, _, _ = decode_and_evaluate(positions[i])
        evaluations += 1
        pbest_fit[i] = fit
        if fit < gbest_fit:
            gbest_fit = fit
            gbest_pos = positions[i].copy()

    iterations_run = 0
    for it in range(iterations):
        w_inertia = INERTIA_START - (INERTIA_START - INERTIA_END) * it / max(1, iterations - 1)
        r1 = rng.uniform(0.0, 1.0, size=(swarm_size, n))
        r2 = rng.uniform(0.0, 1.0, size=(swarm_size, n))
        velocities = (w_inertia * velocities
                      + C1 * r1 * (pbest_pos - positions)
                      + C2 * r2 * (gbest_pos[None, :] - positions))
        velocities = np.clip(velocities, -V_MAX, V_MAX)
        positions = np.clip(positions + velocities, 0.0, 1.0)

        for i in range(swarm_size):
            fit, _, _ = decode_and_evaluate(positions[i])
            evaluations += 1
            if fit < pbest_fit[i]:
                pbest_fit[i] = fit
                pbest_pos[i] = positions[i].copy()
                if fit < gbest_fit:
                    gbest_fit = fit
                    gbest_pos = positions[i].copy()
        iterations_run += 1

    _, ch_local_idx, nearest_ch_pos = decode_and_evaluate(gbest_pos)
    ch_ids = [alive[j].node_id for j in ch_local_idx]

    assignment = {}
    for local_i, nd in enumerate(alive):
        if local_i in set(ch_local_idx.tolist()):
            assignment[nd.node_id] = nd.node_id
        else:
            ch_local = ch_local_idx[nearest_ch_pos[local_i]]
            assignment[nd.node_id] = alive[ch_local].node_id

    wall_clock = time.perf_counter() - t_start
    return PSOResult(
        ch_ids=ch_ids,
        assignment=assignment,
        best_fitness=float(gbest_fit),
        iterations_run=iterations_run,
        swarm_size=swarm_size,
        dimension=n,
        wall_clock_s=wall_clock,
        evaluations=evaluations,
    )
