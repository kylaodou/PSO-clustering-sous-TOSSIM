#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Pilote TOSSIM (Python 2, cote conteneur Docker) : place les capteurs,
configure le canal radio, lance la simulation reelle. Relit topology.h
directement pour rester coherent avec les positions compilees dans le firmware.
Usage : python2 run_tossim.py --rounds 150 --log tossim_run.log
"""
from __future__ import print_function
import sys
import os
import re
import math
import argparse

try:
    from TOSSIM import Tossim
except ImportError:
    print("ERREUR: module TOSSIM introuvable. Compilez d'abord l'application "
          "avec 'make micaz sim' et assurez-vous que le repertoire de build "
          "(build/micaz) est sur le PYTHONPATH.", file=sys.stderr)
    raise

HERE = os.path.dirname(os.path.abspath(__file__))
ROUND_MS = 2400  # PHASE_INFO+CHLIST+JOIN+SCHED+DATA, cf. PSOClustering.h

TX_POWER_DBM = 0.0
PATH_LOSS_EXP = 2.0
REF_DIST_M = 1.0
REF_LOSS_DB = 30.0  # perte de reference a 1 m (CC2420 @2.4GHz)
# Calibre pour que le lien le plus defavorable (~320 m) reste au-dessus du
# bruit de meyer-heavy.txt (~-98 dBm) ; voir docker/README.md pour le detail.


def parse_topology(path):
    text = open(path).read()
    defines = dict(re.findall(r"#define\s+(\w+)\s+(-?\d+)", text))
    positions = {}
    body = re.search(r"node_pos_cm\[[^\]]*\]\[2\]\s*=\s*\{(.*?)\};", text, re.S).group(1)
    pairs = re.findall(r"\{\s*(-?\d+)\s*,\s*(-?\d+)\s*\}", body)
    for idx, (x, y) in enumerate(pairs):
        positions[idx + 1] = (int(x) / 100.0, int(y) / 100.0)  # mote id = idx+1, cm -> m
    bs_pos = (int(defines["BS_X_CM"]) / 100.0, int(defines["BS_Y_CM"]) / 100.0)
    return positions, bs_pos, int(defines["NUM_NODES"])


def gain_db(distance_m):
    d = max(distance_m, REF_DIST_M)
    return TX_POWER_DBM - (REF_LOSS_DB + 10.0 * PATH_LOSS_EXP * math.log10(d / REF_DIST_M))


def find_noise_trace(user_path):
    if user_path and os.path.isfile(user_path):
        return user_path
    candidates = []
    tosroot = os.environ.get("TOSROOT")
    if tosroot:
        candidates.append(os.path.join(tosroot, "tos", "lib", "tossim", "noise", "meyer-heavy.txt"))
        candidates.append(os.path.join(tosroot, "apps", "tutorials", "TestNoise", "meyer-heavy.txt"))
        candidates.append(os.path.join(tosroot, "support", "sdk", "python", "tossim", "meyer-heavy.txt"))
    candidates.append(os.path.join(HERE, "meyer-heavy.txt"))
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=150)
    ap.add_argument("--noise", default=None)
    ap.add_argument("--log", default=os.path.join(HERE, "tossim_run.log"))
    ap.add_argument("--topology", default=os.path.join(HERE, "topology.h"))
    args = ap.parse_args()

    positions, bs_pos, num_nodes = parse_topology(args.topology)
    positions[0] = bs_pos
    ids = sorted(positions.keys())
    print("Topologie chargee : %d capteurs + 1 BS (id 0) en %r" % (num_nodes, bs_pos))

    t = Tossim([])
    radio = t.radio()

    noise_path = find_noise_trace(args.noise)
    if noise_path:
        print("Trace de bruit : %s" % noise_path)
        readings = [int(l.strip()) for l in open(noise_path) if l.strip()]
        readings = readings[:2000] if len(readings) > 2000 else readings
        for mid in ids:
            mote = t.getNode(mid)
            for r in readings:
                mote.addNoiseTraceReading(r)
            mote.createNoiseModel()
    else:
        print("ATTENTION : pas de trace de bruit trouvee -> canal sans pertes "
              "(a documenter comme limite dans le rapport).")

    for i in ids:
        xi, yi = positions[i]
        for j in ids:
            if i == j:
                continue
            xj, yj = positions[j]
            d = math.hypot(xi - xj, yi - yj)
            radio.add(i, j, gain_db(d))

    for mid in ids:
        t.getNode(mid).bootAtTime(mid * 1000)

    log_f = open(args.log, "w")
    t.addChannel("PSO", log_f)

    total_seconds = (args.rounds * ROUND_MS) // 1000 + 5
    end_time = t.time() + t.ticksPerSecond() * total_seconds
    n_events = 0
    while t.time() < end_time:
        if not t.runNextEvent():
            break
        n_events += 1
        if n_events % 200000 == 0:
            print("  ... %d evenements traites (t=%d)" % (n_events, t.time()))

    log_f.flush()
    log_f.close()
    print("Simulation terminee : %d evenements TOSSIM, log ecrit dans %s" % (n_events, args.log))


if __name__ == "__main__":
    main()
