# TP Réseaux sans fil — PSO-clustering avec TOSSIM

**Algorithme :** PSO-clustering, utilisé pour choisir les Cluster Heads (chefs de groupe).
**Simulateur :** TOSSIM, le simulateur de TinyOS.

## Présentation du projet

Ce projet étudie le choix des Cluster Heads avec l'algorithme PSO-clustering dans un réseau de capteurs sans fil. Les essais du réseau sont exécutés avec TOSSIM. Python sert notamment à calculer à l'avance le planning des Cluster Heads, puis à analyser les journaux de simulation et à produire les graphiques.

Le fonctionnement se déroule en trois étapes :

1. `pso_clustering.py` détermine les Cluster Heads pour les différents rounds.
2. Le programme `PSOClusteringC.nc`, écrit en nesC, applique ce planning pendant la simulation TOSSIM. Les capteurs communiquent entre eux et avec la station de base. Les pertes de paquets dépendent notamment du modèle radio utilisé.
3. Les scripts d'analyse lisent les journaux de TOSSIM et produisent les fichiers CSV et les graphiques utilisés dans le rapport.

Le calcul du planning PSO est effectué avant la compilation. Il ne remplace pas la simulation du réseau : les communications et la consommation d'énergie sont simulées par TOSSIM.

## Organisation des fichiers

```text
PSO-Clustering-TOSSIM/
├── tinyos/       # Code TinyOS, scripts et fichiers générés
├── docker/       # Fichiers nécessaires à la compilation et à l'exécution avec Docker
├── results/
│   ├── data/     # Résultats enregistrés au format CSV
│   └── figures/  # Graphiques au format PNG
└── report/       # Rapport final aux formats DOCX, TEX et PDF
```

### Principaux fichiers du dossier `tinyos/`

| Fichier | Rôle |
|---|---|
| `PSOClusteringC.nc` | Décrit le comportement des capteurs et de la station de base pendant la simulation. |
| `PSOClustering.h` | Contient les constantes, les durées des phases et les formats des messages. |
| `PSOClusteringAppC.nc` | Relie les composants TinyOS, notamment la radio et les minuteurs. |
| `Makefile` | Contient les règles de compilation. |
| `network.py` | Définit les positions des capteurs dans le réseau. |
| `pso_clustering.py` | Contient l'algorithme PSO-clustering. |
| `generate_schedule.py` | Exécute le calcul PSO pour les rounds demandés et génère `topology.h` et `ch_schedule.h`. |
| `topology.h`, `ch_schedule.h` | Fichiers générés automatiquement. Il est préférable de ne pas les modifier à la main. |
| `run_tossim.py` | Prépare les capteurs et lance la simulation TOSSIM depuis Python. |
| `analyze_tossim_log.py` | Analyse le journal de simulation, calcule les mesures et crée un fichier CSV. |
| `plot_real_results.py` | Produit les graphiques d'énergie, de capteurs encore actifs et de livraison des données pour le scénario de 100 capteurs. |
| `plot_scalability_real.py` | Produit le graphique comparant les essais avec 50, 100 et 300 capteurs. |

## Pourquoi calculer le planning avant la compilation ?

Pour choisir les Cluster Heads, l'algorithme a besoin de connaître la position et l'énergie des capteurs. Or, la plateforme `micaz` utilisée dans TOSSIM dispose de 4 Ko de RAM, ce qui est trop limité pour exécuter directement l'algorithme PSO complet sur chaque capteur.

Le planning est donc calculé avant la compilation, puis enregistré dans `ch_schedule.h`. Pendant la simulation, TOSSIM s'occupe du réseau : échanges radio, pertes de paquets et consommation d'énergie. Python ne remplace pas cette partie de la simulation.

## Prérequis

- **Docker Desktop** : permet de compiler et d'exécuter TinyOS/TOSSIM dans un conteneur, sans installer TinyOS directement sur Windows. Installer Docker Desktop depuis le site officiel de Docker, puis le démarrer. Pour le lancer depuis PowerShell, si nécessaire :

  ```powershell
  & "C:\Program Files\Docker\Docker\Docker Desktop.exe"
  ```

  Attendre que Docker soit prêt, puis vérifier son fonctionnement avec `docker ps`.

- **Python 3** : utilisé sur Windows pour lancer `generate_schedule.py`, qui calcule le planning PSO. TOSSIM et Python 2 sont exécutés dans le conteneur Docker.

- **MiKTeX ou une autre distribution LaTeX** : nécessaire uniquement si vous souhaitez recompiler le rapport `.tex`. Les fichiers PDF et DOCX déjà produits peuvent être ouverts directement.

## Relancer la simulation principale (100 capteurs)

Les commandes suivantes sont prévues pour PowerShell ou le terminal Windows. Placez-vous d'abord
à la racine du projet, c'est-à-dire dans le dossier `PSO-Clustering-TOSSIM` (celui qui contient
`tinyos/`, `docker/`, `results/` et `report/`) — l'emplacement exact dépend de l'endroit où vous
avez cloné/copié le projet sur votre machine.

```powershell
# 1. Recalculer le planning PSO pour 1000 rounds et 100 capteurs (facultatif)
cd tinyos
python generate_schedule.py 1000 100
cd ..

# 2. Construire l'image Docker et compiler le programme
docker build -t pso-tossim -f docker/Dockerfile .

# 3. Créer un conteneur pour la simulation
docker rm -f pso-run
docker run -d --name pso-run pso-tossim sleep infinity

# 4. Lancer la simulation TOSSIM sur 1000 rounds
docker exec -w /opt/PSOClustering pso-run sh -c "python2 run_tossim.py --rounds 1000 --log resultat.log"

# 5. Copier le journal de simulation sur le PC
docker cp pso-run:/opt/PSOClustering/resultat.log tinyos/resultat.log

# 6. Supprimer le conteneur après la simulation
docker rm -f pso-run

# 7. Analyser le journal et créer le CSV
cd tinyos
python analyze_tossim_log.py resultat.log

# 8. Créer les graphiques
python plot_real_results.py
```

Les graphiques sont enregistrés dans `results/figures/` avec des noms se terminant par `_real.png`. Les données utilisées pour les graphiques sont enregistrées dans `results/data/tossim_real_run.csv`.

### Fichiers de résultats

Le dossier `results/data/` est créé au cours du traitement des résultats, à partir du journal produit par TOSSIM. Il contient notamment les fichiers suivants :

| Fichier | Créé par | Contenu |
|---|---|---|
| `tossim_real_run.csv` | `analyze_tossim_log.py resultat.log` | Une ligne par round, avec les colonnes `round`, `total_energy_j`, `alive`, `data_sent` et `data_delivered`. Ces données servent aux graphiques d'énergie, de survie et de livraison. |
| `scalability_real.csv` | `plot_scalability_real.py` | Les mesures du trafic de contrôle pour les réseaux de 50, 100 et 300 capteurs, comparées aux valeurs attendues selon la formule `2N+1`. |

Les scripts de tracé lisent les données enregistrées dans les CSV. Pour obtenir des graphiques à jour, il faut donc analyser les journaux et mettre à jour les fichiers de résultats avant de relancer les scripts concernés.

**Remarque pour Windows :** les commandes sont adaptées à PowerShell. Si vous utilisez Git Bash ou MSYS, il peut être nécessaire d'ajouter `MSYS_NO_PATHCONV=1` devant certaines commandes `docker run` ou `docker exec` pour éviter que les chemins soient modifiés.

## Comparer des réseaux de 50, 100 et 300 capteurs

Chaque taille de réseau nécessite un planning adapté et une nouvelle compilation, car le programme est compilé pour un nombre précis de capteurs.

Exemple pour 50 capteurs :

```powershell
cd tinyos
python generate_schedule.py 30 50
cd ..

docker build -t pso-tossim-n50 -f docker/Dockerfile .
docker rm -f pso-run50
docker run -d --name pso-run50 pso-tossim-n50 sleep infinity
docker exec -w /opt/PSOClustering pso-run50 sh -c "python2 run_tossim.py --rounds 30 --log n50.log"
docker cp pso-run50:/opt/PSOClustering/n50.log tinyos/n50.log
docker rm -f pso-run50

cd tinyos
python analyze_tossim_log.py n50.log
```

Trente rounds sont utilisés ici pour mesurer le trafic de contrôle. Pour tester 300 capteurs, refaites les étapes avec `300` à la place de `50` et utilisez des noms différents pour l'image Docker et le conteneur, par exemple `pso-tossim-n300` et `pso-run300`.

**Attention pour le test à 300 capteurs :** les essais effectués montrent que la simulation démarre, mais que les messages de contrôle ne sont pas envoyés. Le message `CHLIST`, qui contient la liste des Cluster Heads, devient trop long pour le tampon fourni par TOSSIM. Le problème observé est expliqué dans le journal technique ci-dessous et dans la section IV du rapport.

Après avoir mesuré le trafic de contrôle pour chaque taille de réseau, reportez les valeurs dans le dictionnaire `REAL` en haut du fichier `plot_scalability_real.py`, puis exécutez :

```powershell
python plot_scalability_real.py
```

Après les tests à 50 ou 300 capteurs, régénérez le planning principal avant de reprendre les essais à 100 capteurs :

```powershell
cd tinyos
python generate_schedule.py 1000 100
cd ..
docker build -t pso-tossim -f docker/Dockerfile .
```

## Ouvrir ou recompiler le rapport

### Version Word

Le fichier `report/Rapport_PSO-Clustering_TOSSIM.docx` est déjà disponible. Vous pouvez l'ouvrir directement avec Microsoft Word.

### Version LaTeX

Si MiKTeX est installé, ouvrez un terminal dans le dossier `report/` du projet et lancez deux fois
la compilation :

```powershell
cd report
pdflatex Rapport_PSO-Clustering_TOSSIM.tex
pdflatex Rapport_PSO-Clustering_TOSSIM.tex
```

Les deux compilations permettent notamment de mettre à jour correctement la numérotation et les références.

## Journal technique : problèmes rencontrés et corrections

Cette partie présente les difficultés rencontrées lors de la mise en place de l'environnement et les corrections apportées.

### Choix de l'image Docker

Le dépôt historique `ppa:tinyos-users/ppa` sur Ubuntu/Launchpad ne fournit plus les paquets binaires utilisés au départ. Recompiler `nesc` et `tinyos-main` à partir des sources demanderait aussi d'adapter d'anciens scripts de compilation et de régénérer les liaisons SWIG de TOSSIM pour la version de Python disponible.

Le projet utilise donc l'image Docker communautaire `ucmercedandeslab/tinyos:tossim`, qui contient déjà TinyOS, nesC 1.3.6 et Python 2.7.9, sur une base Debian 8. Elle est d'environ 159 Mo. Elle permet de compiler et d'exécuter le projet dans Docker Desktop sous Windows, sans installer séparément cet environnement sur la machine.

### Problèmes corrigés

1. **Fichier `Makefile` ancien.** Le fichier `tinyos/Makefile` utilisait une ancienne règle de compilation de TinyOS 2.0, avec `include $(MAKERULES)`. L'environnement utilisé attend `TINYOS_ROOT_DIR` et `include $(TINYOS_ROOT_DIR)/Makefile.include`. Sans cette modification, la commande `make micaz sim` échouait avec le message `"micaz sim" does not specify a valid target`.

2. **Modèle radio trop défavorable.** Au départ, `run_tossim.py` utilisait un modèle de perte avec un exposant de 3 et une perte de référence de 40 dB à 1 m. Pour les distances du scénario, le signal devenait trop faible par rapport au bruit radio de `meyer-heavy.txt` (environ -98 dBm), et presque aucun paquet n'arrivait à destination. Le modèle a été remplacé par un modèle d'espace libre avec un exposant de 2 et une perte de référence de 30 dB à 1 m. Dans le scénario testé, ce choix laisse une marge d'environ 18 dB dans le cas le plus défavorable, à une distance d'environ 320 m.

3. **Destinataire des paquets de données.** La fonction `sendData()` envoyait les paquets des capteurs vers les Cluster Heads en diffusion (`AM_BROADCAST_ADDR`), mais la structure `data_msg_t` ne contenait pas de champ indiquant le destinataire. Plusieurs Cluster Heads à portée pouvaient donc accepter le même paquet, ce qui faussait le taux de livraison. Un champ `dstId` a été ajouté à `data_msg_t`, puis un contrôle du destinataire a été ajouté à la réception dans `PSOClustering.h` et `PSOClusteringC.nc`, sur le même principe que celui déjà utilisé pour les messages `JOIN`.

Ces corrections montrent qu'une simulation peut se dérouler sans erreur visible alors que certains paramètres ou traitements produisent des résultats incorrects. Il faut donc vérifier le modèle radio et le traitement des messages avant d'interpréter les résultats.

### Limite observée avec 300 capteurs

Les essais réalisés avec 50 et 100 capteurs ont donné respectivement 85,0 et 157,3 messages de contrôle par round, contre 101 et 201 attendus selon la construction du protocole. L'écart est lié, entre autres, à des messages `CHLIST` qui peuvent être perdus pendant la simulation.

Avec 300 capteurs, aucun message de contrôle n'a été envoyé. Pendant le diagnostic, une vérification temporaire du résultat de `Packet.getPayload()` a montré que le pointeur était `NULL` dès le premier round. Pour cette taille de réseau, le message `CHLIST` peut devoir contenir jusqu'à 15 Cluster Heads, soit 40 octets. Le tampon fourni par TOSSIM ne semble pas accepter cette taille et devient indisponible au-delà d'environ 28 octets, soit environ neuf Cluster Heads.

La simulation continue pourtant à tourner et l'énergie diminue, sans afficher d'erreur. Les communications attendues ne se produisent donc pas. Ce résultat doit être pris en compte lorsqu'on interprète le test à 300 capteurs : il révèle une limite liée à la taille du message dans l'environnement utilisé.

### Autres points à connaître

- **Numérotation des capteurs :** le générateur Python utilise les indices de `0` à `N-1`, alors que les capteurs nesC sont numérotés de `1` à `N` et que la station de base porte le numéro `0`. Le décalage est corrigé par l'ajout de `1` lors de la génération de `ch_schedule.h` et de `topology.h`.
- **Module Python de TOSSIM :** la compilation TinyOS génère les fichiers `TOSSIM.py` et `_TOSSIMmodule.so`. Elle ne génère pas `PSOClusteringAppC.py`. C'est pourquoi `run_tossim.py` utilise `from TOSSIM import Tossim`.
- **Avertissement de compilation :** le compilateur signale que la variable locale `round` dans `PSOClusteringC.nc` porte le même nom qu'une fonction de `math.h`. Cet avertissement n'a pas eu d'effet constaté sur l'exécution et le nom n'a pas été modifié.

## Résultats des essais

Les résultats ci-dessous correspondent à l'exécution de référence (1000 rounds demandés, 1027 rounds réellement simulés, 100 capteurs), consignée dans le projet. Ils peuvent varier légèrement d'une exécution à l'autre, puisque TOSSIM simule des pertes radio en partie aléatoires.

- **Énergie et durée de vie :** le réseau a été suivi sur 1027 rounds. Le premier capteur est mort au round 261 et 68 capteurs sur 100 étaient morts au round 1026 (dernier capteur mort au round 1013).
- **Livraison des données :** taux global mesuré de **55,6 %**, soit **30 296 paquets reçus sur 54 490 paquets émis**, hors paquets de contrôle, sur 1027 rounds.
- **Évolution de la livraison :** la baisse observée à partir du round 800 environ accompagne la diminution du nombre de capteurs actifs. Il reste alors moins de capteurs pour former les groupes, et les liaisons entre les Cluster Heads et la station de base peuvent devenir moins fiables.
- **Comparaison des tailles :** les essais à 50 et 100 capteurs ont produit environ 85 et 157 messages de contrôle par round. À 300 capteurs, aucun message de contrôle n'a été envoyé en raison du problème de taille du message `CHLIST` décrit plus haut.

Les chiffres et les courbes sont présentés dans `report/Rapport_PSO-Clustering_TOSSIM.pdf`, ainsi que dans les fichiers du dossier `results/`.
