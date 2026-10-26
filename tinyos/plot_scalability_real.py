#!/usr/bin/env python3
"""Trace le passage a l'echelle (50/100/300) a partir des 3 executions TOSSIM reelles."""
import os
import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "results", "data")
FIG_DIR = os.path.join(HERE, "..", "results", "figures")

# Mesures reelles (logs CTRL_SENT de TOSSIM). N=300 : getPayload() refuse
# le message CHLIST (40 octets) au-dela de la limite reelle de ~28 octets.
REAL = {
    50:  {"ctrl_per_round": 85.0,  "formula": 101, "events_per_round": 11025},
    100: {"ctrl_per_round": 157.3, "formula": 201, "events_per_round": 24417},
    300: {"ctrl_per_round": 0.0,   "formula": 601, "events_per_round": 18614},
}

with open(os.path.join(DATA_DIR, "scalability_real.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["N", "messages_controle_par_round_reel", "formule_2N+1", "evenements_TOSSIM_par_round"])
    for n, d in REAL.items():
        w.writerow([n, d["ctrl_per_round"], d["formula"], d["events_per_round"]])

COLOR_BLUE = "#2a78d6"
COLOR_RED = "#e34948"
GRID_COLOR = "#e1e0d9"
plt.rcParams.update({
    "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
    "axes.edgecolor": GRID_COLOR, "axes.grid": True, "grid.color": GRID_COLOR,
    "grid.linewidth": 0.8, "font.size": 11, "axes.spines.top": False,
    "axes.spines.right": False, "legend.frameon": False,
})

ns = sorted(REAL.keys())
real_vals = [REAL[n]["ctrl_per_round"] for n in ns]
formula_vals = [REAL[n]["formula"] for n in ns]

fig, ax = plt.subplots(figsize=(6.2, 3.8), dpi=150)
ax.plot(ns, formula_vals, color=GRID_COLOR, linewidth=1.5, linestyle="--",
        marker="o", label="Attendu par construction (2N+1)")
ax.plot(ns, real_vals, color=COLOR_BLUE, linewidth=2, marker="o", markersize=8,
        label="Mesure reelle (TOSSIM)")
ax.scatter([300], [0], color=COLOR_RED, s=90, zorder=5,
           label="N=300 : echec total (message > payload radio)")
ax.set_xlabel("Nombre de capteurs N")
ax.set_ylabel("Messages de controle / round")
ax.set_title("Passage a l'echelle -- mesures reelles TOSSIM", fontsize=11)
ax.set_xticks(ns)
ax.legend(loc="upper left", fontsize=8.5)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "scalability_real.png"))
plt.close(fig)
print("Ecrit scalability_real.png et scalability_real.csv")
