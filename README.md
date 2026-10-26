# TP Réseaux Sans Fil — PSO-clustering sous TOSSIM

**Algorithme :** PSO-clustering (élection des Cluster Heads par essaim de particules)
**Simulateur :** TOSSIM (simulateur de TinyOS)

Tous les résultats de ce projet viennent d'une **exécution réelle** sous TOSSIM — pas d'un
calcul analytique. La seule partie en Python exécutée *avant* la compilation
(`pso_clustering.py`) est l'algorithme PSO lui-même (nécessaire pour décider qui est Cluster
Head), pas un simulateur réseau de substitution.

## Vue d'ensemble en 3 points

1. **`pso_clustering.py` calcule** qui sera Cluster Head à chaque round (algorithme réel, mais
   exécuté une fois à l'avance, hors-ligne — voir "Pourquoi" plus bas).
2. **`PSOClusteringC.nc`** (le firmware, écrit en nesC) applique ce planning dans TOSSIM : chaque
   capteur simulé collecte son énergie, rejoint son chef, envoie ses données, perd parfois des
   paquets à cause du bruit radio réellement simulé.
3. **Les scripts d'analyse** (`analyze_tossim_log.py`, `plot_*.py`) lisent le résultat produit par
   TOSSIM et en sortent les courbes/chiffres du rapport.

## Structure du dossier

```
PSO-Clustering-TOSSIM/
├── tinyos/                    ← tout le code (voir détail ci-dessous)
├── docker/                    ← environnement pour compiler/exécuter sous Windows
├── results/
│   ├── data/                  ← CSV produits par les vraies exécutions TOSSIM
│   └── figures/                ← courbes (PNG), toutes issues de données réelles
└── report/                     ← rapport final (.docx, .tex, .pdf)
```

### Détail de `tinyos/`

| Fichier | Rôle |
|---|---|
| `PSOClusteringC.nc` | Le programme principal : comportement d'un capteur (ou de la BS) dans TOSSIM |
| `PSOClustering.h` | Constantes (modèle radio, durées des phases) et formats des messages |
| `PSOClusteringAppC.nc` | Câblage des composants TinyOS (radio, minuteurs) |
| `Makefile` | Recette de compilation |
| `network.py` | Déploiement aléatoire des capteurs (positions) |
| `pso_clustering.py` | **L'algorithme PSO-clustering** lui-même |
| `generate_schedule.py` | Fait tourner `pso_clustering.py` round par round et écrit `topology.h` / `ch_schedule.h` |
| `topology.h`, `ch_schedule.h` | **Générés automatiquement**, ne pas éditer à la main |
| `run_tossim.py` | Pilote TOSSIM depuis Python (place les capteurs, lance la simulation) |
| `analyze_tossim_log.py` | Lit le résultat de TOSSIM, calcule les métriques, écrit le CSV |
| `plot_real_results.py` | Trace énergie / capteurs vivants / taux de livraison (scénario N=100) |
| `plot_scalability_real.py` | Trace le graphique de passage à l'échelle (50/100/300) |

### Pourquoi un calcul Python *avant* la compilation ?

PSO-clustering a besoin de connaître la position et l'énergie de tous les capteurs pour choisir
les chefs de groupe. Problème : la plateforme simulée par TOSSIM (« micaz ») n'a que **4 Ko de
RAM**, bien trop peu pour faire tourner cet algorithme en direct dessus. On le calcule donc une
fois, avant de compiler, et le résultat est gravé dans le firmware (`ch_schedule.h`). Tout le
reste (radio, pertes de paquets, énergie réellement consommée) est simulé par TOSSIM, pas par
Python.

## Pré-requis (installation de zéro)

- **Docker Desktop** (pour compiler/exécuter TOSSIM sans installer TinyOS sur Windows) :
  télécharger depuis docker.com, installer, puis le démarrer une fois (icône baleine dans la
  barre des tâches). Pour le relancer en ligne de commande :
  `& "C:\Program Files\Docker\Docker\Docker Desktop.exe"` puis attendre ~1 min qu'il soit prêt
  (`docker ps` doit répondre sans erreur).
- **Python 3** sur la machine hôte, uniquement pour `generate_schedule.py` (le calcul PSO
  hors-ligne) — tout le reste (TOSSIM, Python 2) tourne **dans** le conteneur Docker, rien d'autre
  à installer pour ça.
- **MiKTeX** (ou toute distribution LaTeX), seulement si vous voulez recompiler le rapport
  `.tex` vous-même ; sinon le `.pdf`/`.docx` déjà généré se lit tel quel.

## Étape par étape : relancer la simulation principale (N=100)

```bash
cd "d:\Ecole\Master 1\reseau sans fil\PSO-Clustering-TOSSIM"

# 1. (Optionnel) Recalculer le planning PSO, ex. pour 1000 rounds :
cd tinyos
python generate_schedule.py 1000 100
cd ..

# 2. Construire l'image Docker (compile le firmware dedans)
docker build -t pso-tossim -f docker/Dockerfile .

# 3. Démarrer un conteneur
docker rm -f pso-run
docker run -d --name pso-run pso-tossim sleep infinity

# 4. Lancer la vraie simulation TOSSIM (ici 1000 rounds)
docker exec -w /opt/PSOClustering pso-run sh -c "python2 run_tossim.py --rounds 1000 --log resultat.log"

# 5. Récupérer le log sur votre PC
docker cp pso-run:/opt/PSOClustering/resultat.log tinyos/resultat.log

# 6. Éteindre le conteneur (plus besoin de Docker pour la suite)
docker rm -f pso-run

# 7. Analyser le résultat (taux de livraison, morts, etc.) et produire le CSV
cd tinyos
python analyze_tossim_log.py resultat.log

# 8. Tracer les courbes (énergie, capteurs vivants, taux de livraison)
python plot_real_results.py
```

Les figures sont écrites dans `results/figures/*_real.png`, le CSV dans
`results/data/tossim_real_run.csv`.

### Contenu de `results/data/`

Ce dossier n'existe pas au départ : il est créé par `analyze_tossim_log.py` et
`plot_scalability_real.py` (étapes 7 et au-dessus), à partir du log brut produit par TOSSIM
(étape 4). Il contient :

| Fichier | Créé par | Contenu |
|---|---|---|
| `tossim_real_run.csv` | `analyze_tossim_log.py resultat.log` | Une ligne par round : `round, total_energy_j, alive, data_sent, data_delivered`. C'est la source des figures d'énergie/survie/livraison. |
| `scalability_real.csv` | `plot_scalability_real.py` | Une ligne par taille de réseau testée (50/100/300) : messages de contrôle par round mesurés vs formule attendue $2N{+}1$. |

C'est ce CSV (et lui seul) qui alimente les courbes du rapport : rien n'est recalculé ou
réinventé au moment de tracer les figures, `plot_real_results.py` ne fait que lire ces colonnes.

**Remarque Windows/PowerShell** : les commandes ci-dessus marchent telles quelles sous
PowerShell. Sous Git Bash/MSYS, préfixez les commandes `docker run`/`docker exec` par
`MSYS_NO_PATHCONV=1` pour éviter que les chemins soient mal interprétés.

## Étape par étape : le passage à l'échelle (50 / 100 / 300)

Chaque taille de réseau demande sa propre topologie + sa propre image Docker (le firmware est
compilé spécifiquement pour N capteurs) :

```bash
cd tinyos
python generate_schedule.py 30 50          # 30 rounds suffisent pour mesurer le trafic de controle
cd ..
docker build -t pso-tossim-n50 -f docker/Dockerfile .
docker rm -f pso-run50
docker run -d --name pso-run50 pso-tossim-n50 sleep infinity
docker exec -w /opt/PSOClustering pso-run50 sh -c "python2 run_tossim.py --rounds 30 --log n50.log"
docker cp pso-run50:/opt/PSOClustering/n50.log tinyos/n50.log
docker rm -f pso-run50
cd tinyos && python analyze_tossim_log.py n50.log
```

Répétez avec `300` à la place de `50` (noms d'image/conteneur différents, ex. `pso-tossim-n300`).
**Attention** : à N=300, la simulation tourne normalement mais **aucun message n'est jamais
envoyé** — c'est un résultat réel, diagnostiqué et documenté dans `docker/README.md` (section 6)
et dans le rapport (section IV) : le message qui annonce les chefs de groupe dépasse la taille
maximale acceptée par la radio simulée au-delà d'environ 28 octets.

Une fois les 3 valeurs mesurées (`messages de contrôle / round` affiché par
`analyze_tossim_log.py`), reportez-les dans `plot_scalability_real.py` (dictionnaire `REAL` en
haut du fichier) puis relancez `python plot_scalability_real.py`.

**Important** : après avoir testé 50/300, remettez la topologie principale en place avant de
refaire tourner quoi que ce soit sur N=100 : `python generate_schedule.py 1000 100` puis
`docker build -t pso-tossim -f docker/Dockerfile .`.

## Compiler les rapports

**Word** : `report/Rapport_PSO-Clustering_TOSSIM.docx` est déjà généré et à jour — ouvrez-le
directement avec Microsoft Word.

**LaTeX** (MiKTeX déjà installé sur cette machine) :
```bash
cd "d:\Ecole\Master 1\reseau sans fil\PSO-Clustering-TOSSIM\report"
pdflatex Rapport_PSO-Clustering_TOSSIM.tex
pdflatex Rapport_PSO-Clustering_TOSSIM.tex
```
(2 passes nécessaires pour que la numérotation se stabilise.)

## Résultats actuels (déjà obtenus, réels)

- **Énergie** : réseau simulé sur 1027 rounds réels, 69 capteurs sur 100 morts (1ère mort au
  round 251).
- **Taux de livraison** : 55,9 % mesuré (30 410 paquets reçus / 54 371 émis).
- **Passage à l'échelle** : fonctionne à N=50 (85 messages/round) et N=100 (157 messages/round) ;
  **échec total mesuré et diagnostiqué à N=300** (limite réelle de la radio simulée).

Tout est détaillé dans `report/Rapport_PSO-Clustering_TOSSIM.pdf` et dans `docker/README.md`
(journal complet des difficultés rencontrées, utile pour la partie « critique du simulateur »).
