#!/usr/bin/env python3
"""
Parse le log dbg() d'une execution reelle de TOSSIM (run_tossim.py) et
produit results/data/tossim_real_run.csv + un resume texte (taux de
livraison, morts, messages). Tourne en Python 3 normal, pas besoin de TOSSIM.
"""
import re
import sys
import os
import csv
import argparse
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_CSV = os.path.join(HERE, "..", "results", "data", "tossim_real_run.csv")
NUM_NODES = 100

RE_ENERGY = re.compile(r"ENERGY_TOTAL,(\d+),(\d+)")
RE_DATA_BS = re.compile(r"DATA_BS,(\d+),(\d+),(\d+)")
RE_DATA_ATTEMPT = re.compile(r"DATA_ATTEMPT,(\d+),(\d+)")
RE_DEAD = re.compile(r"DEAD,(\d+),(\d+)")
RE_CTRL_SENT = re.compile(r"CTRL_SENT,(\d+),(\d+)")


def analyze(log_path):
    energy_by_round = {}
    delivered_by_round = defaultdict(int)
    sent_by_round = defaultdict(int)
    ctrl_by_round = defaultdict(int)
    deaths = []

    with open(log_path, errors="replace") as f:
        for line in f:
            m = RE_ENERGY.search(line)
            if m:
                r, mj = int(m.group(1)), int(m.group(2))
                energy_by_round[r] = mj / 1000.0
                continue
            m = RE_DATA_BS.search(line)
            if m:
                r, _ch, n = int(m.group(1)), int(m.group(2)), int(m.group(3))
                delivered_by_round[r] += n
                continue
            m = RE_DATA_ATTEMPT.search(line)
            if m:
                r, _id = int(m.group(1)), int(m.group(2))
                sent_by_round[r] += 1
                continue
            m = RE_DEAD.search(line)
            if m:
                deaths.append((int(m.group(1)), int(m.group(2))))
                continue
            m = RE_CTRL_SENT.search(line)
            if m:
                ctrl_by_round[int(m.group(1))] += 1
                continue

    all_rounds = sorted(set(energy_by_round) | set(delivered_by_round) | set(sent_by_round))
    if not all_rounds:
        print("ATTENTION : aucun evenement PSO reconnu dans le log. "
              "Verifiez le format des lignes dbg (voir README).")
        return

    # nombre de capteurs vivants par round = 100 - morts cumulees jusque-la
    deaths_by_round = defaultdict(int)
    for _id, r in deaths:
        deaths_by_round[r] += 1
    cumulative_dead = 0
    alive_by_round = {}
    for r in all_rounds:
        cumulative_dead += deaths_by_round.get(r, 0)
        alive_by_round[r] = NUM_NODES - cumulative_dead

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["round", "total_energy_j", "alive", "data_sent", "data_delivered"])
        for r in all_rounds:
            w.writerow([r, energy_by_round.get(r, ""), alive_by_round[r],
                        sent_by_round.get(r, 0), delivered_by_round.get(r, 0)])

    total_sent = sum(sent_by_round.values())
    total_delivered = sum(delivered_by_round.values())
    ratio = (total_delivered / total_sent * 100.0) if total_sent else 0.0

    print("=== Resultats reels TOSSIM (PSOClustering, N=100) ===")
    print("Rounds observes         : %d (0..%d)" % (len(all_rounds), max(all_rounds)))
    print("Paquets de donnees emis : %d" % total_sent)
    print("Paquets recus par la BS : %d" % total_delivered)
    print("Taux de livraison global: %.2f%%" % ratio)
    if deaths:
        first = min(r for _, r in deaths)
        last = max(r for _, r in deaths)
        print("Premiere mort de noeud (FND) a round : %d" % first)
        print("Nombre total de morts sur la fenetre : %d / %d" % (len(deaths), NUM_NODES))
        print("Derniere mort observee a round        : %d" % last)
    else:
        print("Aucun noeud mort observe sur la fenetre simulee.")
    if ctrl_by_round:
        stable_rounds = [r for r in all_rounds[:20] if r in ctrl_by_round]
        if stable_rounds:
            avg_ctrl = sum(ctrl_by_round[r] for r in stable_rounds) / len(stable_rounds)
            print("Messages de controle / round (20 premiers rounds, moyenne) : %.1f" % avg_ctrl)
    print("CSV ecrit : %s" % OUT_CSV)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("log", nargs="?", default=os.path.join(HERE, "tossim_run.log"))
    args = ap.parse_args()
    analyze(args.log)
