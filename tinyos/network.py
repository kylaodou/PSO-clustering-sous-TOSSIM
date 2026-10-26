"""Topologie du reseau : deploiement aleatoire des noeuds et de la station de base."""

from dataclasses import dataclass, field
import math
import numpy as np

FIELD_X = 200.0
FIELD_Y = 200.0
BS_X = 100.0
BS_Y = 250.0
E_INIT = 0.5  # Joules, homogene (PSO-clustering : pas de noeuds "avances" -> homogene)


@dataclass
class Node:
    node_id: int
    x: float
    y: float
    energy: float = E_INIT
    alive: bool = True

    def dist_to(self, x: float, y: float) -> float:
        return math.hypot(self.x - x, self.y - y)

    def dist_to_bs(self) -> float:
        return self.dist_to(BS_X, BS_Y)


def deploy_network(n_nodes: int, seed: int) -> list[Node]:
    """Deploiement aleatoire uniforme de n_nodes capteurs sur 200x200 m."""
    rng = np.random.default_rng(seed)
    xs = rng.uniform(0.0, FIELD_X, n_nodes)
    ys = rng.uniform(0.0, FIELD_Y, n_nodes)
    return [Node(node_id=i, x=float(xs[i]), y=float(ys[i])) for i in range(n_nodes)]


def alive_nodes(nodes: list[Node]) -> list[Node]:
    return [n for n in nodes if n.alive]


def total_energy(nodes: list[Node]) -> float:
    return sum(max(n.energy, 0.0) for n in nodes)
