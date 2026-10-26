"""
Precalcule le planning PSO (topology.h + ch_schedule.h) avant compilation :
TOSSIM cible un mote a 4 Ko de RAM, trop peu pour l'essaim PSO en direct.
Usage : python generate_schedule.py [rounds] [nombre_de_noeuds]
"""
import sys
import os

from network import deploy_network, FIELD_X, FIELD_Y, BS_X, BS_Y, E_INIT
from pso_clustering import run_pso

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 42
NUM_NODES = 100  # peut etre ecrase par le 2e argument en ligne de commande

# Modele radio de premier ordre -- memes constantes que PSOClustering.h,
# utilisees ici uniquement pour estimer qui aura encore de la batterie.
E_ELEC = 50e-9
E_FS = 10e-12
E_MP = 1.3e-15
D0 = (E_FS / E_MP) ** 0.5
CTRL_BITS = 200


def tx_cost(bits, d):
    if d < D0:
        return bits * E_ELEC + bits * E_FS * d * d
    return bits * E_ELEC + bits * E_MP * d ** 4


def rx_cost(bits):
    return bits * E_ELEC


def precompute(num_rounds: int):
    nodes = deploy_network(NUM_NODES, seed=SEED)
    schedule = []

    for r in range(num_rounds):
        alive = [n for n in nodes if n.alive]
        if not alive:
            schedule.append([])
            continue

        res = run_pso(alive, seed=SEED + r)
        ch_ids = set(res.ch_ids)
        schedule.append(sorted(ch_ids))

        # cout de la phase de controle (INFO + JOIN), pour que le round
        # suivant voie une energie residuelle realiste
        for n in alive:
            d_bs = n.dist_to_bs()
            n.energy -= tx_cost(CTRL_BITS, d_bs) + rx_cost(CTRL_BITS)
            if n.node_id not in ch_ids:
                ch = next(x for x in alive if x.node_id in ch_ids)
                n.energy -= tx_cost(CTRL_BITS, n.dist_to(ch.x, ch.y))
            if n.energy <= 0:
                n.energy = 0
                n.alive = False

    return nodes, schedule


def write_headers(nodes, schedule):
    topo_path = os.path.join(HERE, "topology.h")
    with open(topo_path, "w") as f:
        f.write("// Genere par generate_schedule.py -- positions des capteurs et de la BS.\n")
        f.write("#ifndef TOPOLOGY_H\n#define TOPOLOGY_H\n\n")
        f.write(f"#define NUM_NODES {NUM_NODES}\n")
        f.write(f"#define FIELD_X_CM {int(FIELD_X*100)}\n")
        f.write(f"#define FIELD_Y_CM {int(FIELD_Y*100)}\n")
        f.write(f"#define BS_X_CM {int(BS_X*100)}\n")
        f.write(f"#define BS_Y_CM {int(BS_Y*100)}\n\n")
        f.write("static const int16_t node_pos_cm[NUM_NODES][2] = {\n")
        for nd in nodes:
            f.write(f"  {{ {int(round(nd.x*100))}, {int(round(nd.y*100))} }},\n")
        f.write("};\n\n#endif // TOPOLOGY_H\n")

    sched_path = os.path.join(HERE, "ch_schedule.h")
    max_ch = max((len(r) for r in schedule), default=1) or 1
    with open(sched_path, "w") as f:
        f.write("// Genere par generate_schedule.py -- planning PSO precalcule (voir rapport,\n")
        f.write("// section Methodologie : pourquoi ce calcul est fait hors-ligne).\n")
        f.write("#ifndef CH_SCHEDULE_H\n#define CH_SCHEDULE_H\n\n")
        f.write(f"#define NUM_DEMO_ROUNDS {len(schedule)}\n")
        f.write(f"#define MAX_CH {max_ch}\n\n")
        f.write("// ch_schedule[round][i] = TOS_NODE_ID du i-eme CH (0xFFFF = inutilise).\n")
        f.write("// +1 car les motes capteurs sont numerotes 1..NUM_NODES (mote 0 = BS).\n")
        f.write(f"static const uint16_t ch_schedule[NUM_DEMO_ROUNDS][MAX_CH] = {{\n")
        for round_chs in schedule:
            ids = [cid + 1 for cid in round_chs] + [0xFFFF] * (max_ch - len(round_chs))
            f.write("  { " + ", ".join(str(i) for i in ids) + " },\n")
        f.write("};\n\n")
        f.write("static const uint8_t ch_schedule_count[NUM_DEMO_ROUNDS] = {\n  ")
        f.write(", ".join(str(len(r)) for r in schedule))
        f.write("\n};\n\n#endif // CH_SCHEDULE_H\n")

    print(f"Ecrit {topo_path}")
    print(f"Ecrit {sched_path} ({len(schedule)} rounds, MAX_CH={max_ch})")


if __name__ == "__main__":
    n_rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    if len(sys.argv) > 2:
        NUM_NODES = int(sys.argv[2])
    nodes, schedule = precompute(n_rounds)
    write_headers(nodes, schedule)
