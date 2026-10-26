#!/usr/bin/env python3
"""Trace les 3 courbes a partir de tossim_real_run.csv (donnees reelles TOSSIM)."""
import os
import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "..", "results", "data", "tossim_real_run.csv")
FIG_DIR = os.path.join(HERE, "..", "results", "figures")
os.makedirs(FIG_DIR, exist_ok=True)

COLOR_BLUE = "#2a78d6"
COLOR_AQUA = "#1baf7a"
COLOR_VIOLET = "#4a3aa7"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID_COLOR = "#e1e0d9"
SURFACE = "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "axes.edgecolor": GRID_COLOR, "axes.grid": True, "grid.color": GRID_COLOR,
    "grid.linewidth": 0.8, "font.size": 11, "axes.spines.top": False,
    "axes.spines.right": False, "legend.frameon": False,
})

rounds, energy, alive, sent, delivered = [], [], [], [], []
with open(CSV_PATH) as f:
    for row in csv.DictReader(f):
        rounds.append(int(row["round"]))
        energy.append(float(row["total_energy_j"]) if row["total_energy_j"] else np.nan)
        alive.append(int(row["alive"]))
        sent.append(int(row["data_sent"]))
        delivered.append(int(row["data_delivered"]))

rounds = np.array(rounds)
energy = np.array(energy)
alive = np.array(alive)
sent = np.array(sent, dtype=float)
delivered = np.array(delivered, dtype=float)

# --- energie residuelle totale (vraie, mesuree par TOSSIM) ---
fig, ax = plt.subplots(figsize=(6.2, 3.6), dpi=150)
ax.plot(rounds, energy, color=COLOR_BLUE, linewidth=1.6)
ax.set_xlabel("Round")
ax.set_ylabel("Energie residuelle totale (J)")
ax.set_title("Energie residuelle du reseau (execution reelle TOSSIM, N=100)", fontsize=10.5)
ax.set_ylim(bottom=0)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "energy_vs_rounds_real.png"))
plt.close(fig)

# --- noeuds vivants ---
fig, ax = plt.subplots(figsize=(6.2, 3.6), dpi=150)
ax.plot(rounds, alive, color=COLOR_VIOLET, linewidth=1.8)
ax.set_xlabel("Round")
ax.set_ylabel("Capteurs vivants")
ax.set_title("Capteurs vivants (execution reelle TOSSIM, N=100)", fontsize=10.5)
ax.set_ylim(0, 105)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "alive_vs_rounds_real.png"))
plt.close(fig)

# --- taux de livraison, fenetre glissante ---
window = 20
ratio = np.full(len(rounds), np.nan)
for i in range(len(rounds)):
    lo = max(0, i - window + 1)
    s, d = sent[lo:i+1].sum(), delivered[lo:i+1].sum()
    if s > 0:
        ratio[i] = d / s * 100.0

overall = delivered.sum() / sent.sum() * 100.0 if sent.sum() else 0.0

fig, ax = plt.subplots(figsize=(6.2, 3.6), dpi=150)
ax.plot(rounds, ratio, color=COLOR_AQUA, linewidth=1.4)
ax.axhline(overall, color=INK_MUTED, linewidth=1, linestyle="--",
           label=f"Moyenne globale = {overall:.1f}%")
ax.set_xlabel("Round")
ax.set_ylabel("Taux de livraison (%)")
ax.set_title("Taux de livraison -- execution reelle TOSSIM (N=100)")
ax.set_ylim(0, 105)
ax.legend(loc="lower left")
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "delivery_ratio_vs_rounds_real.png"))
plt.close(fig)

print(f"3 figures ecrites dans {FIG_DIR} (suffixe _real.png)")
print(f"Taux de livraison global : {overall:.2f}%")
print(f"Capteurs vivants a la fin : {alive[-1]}/100 (round {rounds[-1]})")
