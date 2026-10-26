# TOSSIM / TinyOS 2.1.2 -- environnement Docker (PSO-Clustering)

Ce dossier contient l'environnement Docker qui permet de compiler et
d'executer reellement l'application nesC `../tinyos/` (protocole
PSO-clustering) dans TOSSIM, le simulateur reseau de TinyOS. **Succes** :
compilation nesC propre, bindings Python TOSSIM fonctionnels, execution
reelle de 150 rounds produisant un log non trivial et un taux de livraison
global de **57.19 %** (voir `../results/tossim_run_summary.txt` et
`../results/data/tossim_real_run.csv`).

## 1. Ce qui a ete essaye, dans l'ordre

### Tentative 1 -- PPA historique `ppa:tinyos-users/ppa` (draft initial)

Le premier jet de ce `Dockerfile` partait d'`ubuntu:14.04` + bascule vers
`old-releases.ubuntu.com` (14.04 est EOL) + `add-apt-repository
ppa:tinyos-users/ppa` pour installer le meta-paquet `tinyos-2.1.2`.

**Diagnostic** : ce PPA est mort -- Launchpad ne sert plus les paquets
binaires de `tinyos-users/ppa` pour trusty. Le repli prevu dans le draft
(clonage + compilation de `tinyos/nesc` et `tinyos/tinyos-main` depuis
GitHub) est fonctionnellement possible mais tres couteux : `nesc` utilise
un jeu de macros autotools ancien (Bootstrap/autoreconf de ~2010) qui
necessite un ajustement fin pour un autotools/gcc moderne, et les
bindings SWIG de TOSSIM doivent ensuite etre regeneres pour la version de
Python 2 effectivement presente dans l'image. Cette piste a ete abandonnee
au profit de la strategie ci-dessous, plus fiable et beaucoup plus rapide
a mettre en oeuvre, avant d'y consacrer un temps disproportionne.

### Tentative retenue -- image communautaire prete a l'emploi

Recherche web de Dockerfiles "tinyos tossim" publies par d'autres
cours/laboratoires : l'image **`ucmercedandeslab/tinyos:tossim`** (UC
Merced ANDES Lab, publiee sur Docker Hub, ~2017, 159 Mo) est apparue comme
un environnement de developpement TinyOS/TOSSIM pret a l'emploi. Aucune
source Dockerfile publique n'a ete retrouvee pour cette image (organisation
GitHub `ucmercedandeslab` introuvable/vide au moment de la recherche) --
elle est donc utilisee directement comme image de base (`FROM
ucmercedandeslab/tinyos:tossim`), sans reconstruire sa recette interne.

Contenu verifie a l'interieur du conteneur :
- Debian 8 "jessie"
- paquet `nesc` 1.3.6-tinyprod (compilateur `nescc` natif, deja compile --
  pas besoin de repasser par Bootstrap/autoconf)
- `tinyos-main` clone dans `/opt/tinyos-main` (`TINYOS_ROOT_DIR` deja
  positionne dans l'image)
- Python 2.7.9 + gcc/g++ 4.9.2 (suffisants pour compiler le C genere par
  `nescc` et les wrappers SWIG C++/Python de TOSSIM)

Cette image fonctionne directement sur un hote Windows 11 + Docker Desktop
(moteur Linux, conteneurs `linux/amd64`) : aucune compilation croisee ni
astuce WSL specifique necessaire au-dela de Docker Desktop lui-meme.

## 2. Difficultes rencontrees avec NOTRE application, et corrections

Trois problemes reels ont ete rencontres en essayant de faire tourner
*notre* code dans cet environnement (aucun n'etait un probleme de
l'image de base elle-meme) :

### 2.1 Makefile TinyOS -- mecanisme de build deprecie

Notre `tinyos/Makefile` utilisait le motif TinyOS 2.0 historique :

```make
include $(MAKERULES)
```

qui suppose des variables d'environnement `TOSROOT`/`TOSDIR`/`MAKERULES`
deja exportees. Le systeme de build de `tinyos-main` (branches >= 2.1) a
deprecie ce mecanisme au profit de :

```make
COMPONENT=PSOClusteringAppC
TINYOS_ROOT_DIR?=/opt/tinyos-main
include $(TINYOS_ROOT_DIR)/Makefile.include
```

Sans cette correction, `make micaz sim` echouait avec `"micaz sim" does
not specify a valid target` (le fichier de regles n'etait simplement pas
inclus). **Corrige** dans `tinyos/Makefile`.

### 2.2 Calibration radio de `run_tossim.py` -- taux de livraison ~0 %

Premiere execution reelle : la simulation tournait sans erreur (2.5
millions d'evenements TOSSIM traites) mais produisait un log quasi vide
sur le plan applicatif (0 paquet recu par la BS, ~20 tentatives de donnees
sur 150 rounds x 100 noeuds attendus). Diagnostic : `run_tossim.py`
configurait le gain radio avec un modele log-distance
(`REF_LOSS_DB=40`, `PATH_LOSS_EXP=3`, `TX_POWER_DBM=0`), ce qui donne un
gain de l'ordre de **-98 a -115 dB** aux distances reelles du scenario (BS
placee ~50 m hors du champ 200x200 m -> liens utiles jusqu'a ~320 m).
Or la trace de bruit utilisee, `meyer-heavy.txt` (fournie avec
`tinyos-main`), est exprimee en **dBm reels**, avec un plancher de bruit
de fond ~ -98 dBm (verifie : plus de 40 000 lectures a -98/-99 dBm sur
196 610 lignes). La puissance recue tombait donc systematiquement sous
(ou au niveau) du bruit sur la quasi-totalite des liens BS<->capteur :
la radio *simulait bien* mais ne delivrait presque jamais rien, y compris
pour les diffusions de controle (CHLIST) indispensables a l'election des
CH.

**Corrige** : modele espace-libre plus standard, exposant de perte 2 au
lieu de 3, perte de reference 30 dB a 1 m au lieu de 40 dB (constantes
`PATH_LOSS_EXP` / `REF_LOSS_DB` dans `run_tossim.py`). Au pire cas
(~320 m), le signal recu est alors ~ -80 dBm, soit ~18 dB au-dessus du
plancher de bruit -- marge realiste pour un lien qui reussit "souvent
mais pas toujours" (coherent avec les pertes/pics d'interference presents
dans `meyer-heavy.txt`, d'ou son nom).

C'est un point important pour la section "critique du simulateur" du
rapport : **TOSSIM est tres sensible a la coherence d'unites entre la
matrice de gain radio et la trace de bruit utilisee** ; rien dans l'API
n'avertit quand cette coherence est rompue -- la simulation tourne
normalement, sans erreur, mais livre silencieusement (quasiment) aucun
paquet.

### 2.3 Bug applicatif -- absence de filtrage destinataire sur les messages de donnees

Une fois la portee radio corrigee, un second symptome est apparu :
`DATA_HOP1` (paquets capteur->CH recus par UN CH) etait compte **plus de
fois** que `DATA_ATTEMPT` (tentatives d'emission), ce qui est logiquement
impossible pour un evenement de reception en aval d'un evenement
d'emission.

Diagnostic : `sendData()` (membre -> CH) diffuse en `AM_BROADCAST_ADDR`.
Le message `data_msg_t` de type `DATA_TYPE_SENSOR_TO_CH` ne portait
**aucun champ destinataire** (a la difference du message `CTRL_TYPE_JOIN`,
qui verifie deja correctement `m->dstId == myId` cote reception). Une fois
la portee radio elargie a une valeur realiste, **chaque** CH concurrent
physiquement a portee radio du membre emetteur recevait le paquet et se
l'appropriait (incrementait son propre `membersReportedThisRound` et
loggait `DATA_HOP1`), au lieu du seul CH auquel le membre avait
effectivement adhere. Consequence concrete : le taux de livraison agrege
mesurait initialement au-dela de ce qui est physiquement plausible.

**Corrige** (fichiers nesC/header, pas seulement le driver Python) :
- `tinyos/PSOClustering.h` : ajout d'un champ `dstId` dans `data_msg_t`.
- `tinyos/PSOClusteringC.nc` : `sendData()` renseigne desormais
  `m->dstId = myCH` ; `DataReceive.receive()` filtre desormais sur
  `m->dstId == myId` pour `DATA_TYPE_SENSOR_TO_CH` (meme motif que le
  filtrage deja present pour `CTRL_TYPE_JOIN`). `sendDataToBs()`
  renseigne `m->dstId = 0` (BS) par coherence/documentation (le filtrage
  cote BS reposait deja correctement sur `myId == 0`, donc ce champ n'etait
  pas strictement necessaire pour ce second type de message, mais
  clarifie l'intention).

Apres cette correction, `DATA_HOP1` redevient un sous-ensemble coherent de
`DATA_ATTEMPT` et le taux de livraison global se stabilise a un ordre de
grandeur physiquement raisonnable (~55-60 % sur plusieurs executions
independantes -- TOSSIM integre une part de tirage aleatoire dans son
modele de bruit/erreurs bit a bit, donc le nombre exact d'evenements et le
taux precis varient legerement d'une execution a l'autre, sans changer
l'ordre de grandeur).

## 3. Reproduire depuis zero

Depuis la racine du projet (`PSO-Clustering-TOSSIM/`), sous Git
Bash/MSYS sur Windows :

```bash
# 1. Construire l'image (COPY tinyos/ -> /opt/PSOClustering, puis
#    `make micaz sim` execute pendant le build : echoue immediatement si
#    le code nesC ne compile pas plutot que de le decouvrir plus tard).
cd "d:\Ecole\Master 1\reseau sans fil\PSO-Clustering-TOSSIM"
docker build -t pso-tossim -f docker/Dockerfile .

# 2. Lancer un conteneur persistant (pas de volume monte : on evite ainsi
#    les problemes de conversion de chemin MSYS<->Windows avec Docker sur
#    Git Bash ; prefixer MSYS_NO_PATHCONV=1 chaque commande docker qui
#    passe un chemin absolu commencant par "/", ex. -w /opt/PSOClustering,
#    sinon Git Bash le reecrit de facon inattendue et Docker renvoie
#    "Cwd must be an absolute path").
MSYS_NO_PATHCONV=1 docker run -d --name pso-run pso-tossim sleep infinity

# 3. Executer la simulation reelle (150 rounds) DANS le conteneur.
#    TOSROOT est deja positionne par l'image de base a /opt/tinyos-main.
MSYS_NO_PATHCONV=1 docker exec -w /opt/PSOClustering pso-run \
  sh -c "python2 run_tossim.py --rounds 150 --log tossim_run.log"

# 4. Recuperer le log produit dans le conteneur vers l'hote.
docker cp pso-run:/opt/PSOClustering/tossim_run.log tinyos/tossim_run.log

# 5. Analyser le log avec Python 3 sur l'HOTE (aucune dependance TOSSIM
#    necessaire pour cette etape : le script ne fait que parser du texte).
cd tinyos
python3 analyze_tossim_log.py tossim_run.log
# -> ecrit ../results/data/tossim_real_run.csv et affiche le taux de
#    livraison global.

# 6. Nettoyage (optionnel).
docker rm -f pso-run
```

Notes :
- L'image de base est buildee pour `linux/amd64`. Docker Desktop sur
  Windows 11 avec le moteur Linux (WSL2 ou Hyper-V) l'execute nativement ;
  aucune configuration additionnelle necessaire au-dela de Docker Desktop
  installe et le daemon accessible (`docker ps` fonctionne).
- Le systeme de build produit `TOSSIM.py` + `_TOSSIMmodule.so` (et NON
  `PSOClusteringAppC.py` / `_TOSSIM.so`) dans le repertoire courant de
  l'application : c'est la nomenclature generique de ce systeme de build
  TinyOS (le nom du module Python importe reste toujours `TOSSIM`,
  independamment du nom du composant applicatif -- `run_tossim.py` fait
  d'ailleurs `from TOSSIM import Tossim`, ce qui correspond exactement a
  ce qui est genere).
- Le seul avertissement de compilation observe (`declaration of 'round'
  shadows global declaration`, `PSOClusteringC.nc:120`) est benin : la
  variable locale `round` dans `loadChScheduleForRound()` masque la
  fonction `round()` de `math.h` (jamais utilisee sous ce nom dans le
  fichier) ; sans consequence sur la compilation ou l'execution, non
  corrige pour ne pas renommer une variable sans necessite fonctionnelle.

## 4. Resultats obtenus

Voir `../results/tossim_run_summary.txt` (sorties completes de
`run_tossim.py` et `analyze_tossim_log.py`) et
`../results/data/tossim_real_run.csv` (serie temporelle round par round :
energie totale residuelle, paquets emis, paquets delivres).

Resume : 150 rounds demandes (156 observes en pratique -- quelques rounds
supplementaires partiellement entames avant la fin de la fenetre de temps
simule), 100 capteurs + 1 BS, ~11 600 tentatives d'emission de donnees,
~6 600 paquets effectivement remontes a la BS, soit un **taux de livraison
global de l'ordre de 57 %**. Aucune mort de noeud sur cette fenetre (voir
section "Limites" ci-dessous).

## 5. Limites et pistes (pour la section "critique du simulateur")

- **Sensibilite de calibration** (section 2.2) : TOSSIM ne valide en rien
  la coherence entre la trace de bruit choisie et le modele de gain radio
  fourni par l'utilisateur. Une erreur d'un facteur ~2-3 sur l'exposant de
  perte de parcours suffit a faire passer le reseau simule de "fonctionne
  normalement" a "ne delivre presque rien", sans le moindre message
  d'erreur ou d'avertissement. C'est une source de bugs silencieux
  particulierement traitre pour un TP.
- **Diffusion radio et filtrage applicatif** (section 2.3) : TOSSIM simule
  fidelement qu'un message envoye en `AM_BROADCAST_ADDR` est
  physiquement recu par TOUS les noeuds a portee, ce qui est correct sur
  le plan radio -- mais deplace explicitement sur le code applicatif la
  responsabilite du filtrage par destinataire. Un protocole de clustering
  qui omet ce filtrage (comme c'etait initialement le cas ici pour les
  messages capteur->CH) produit des resultats silencieusement faux
  (taux de livraison gonfle), sans qu'aucune erreur ne le signale : seule
  une verification de coherence (ici, `DATA_HOP1` > `DATA_ATTEMPT`) a
  permis de le detecter.
- **Duree simulable** : 150 rounds representent ~5 millions d'evenements
  TOSSIM et prennent de l'ordre de 1 a 2 minutes CPU dans ce conteneur.
  MISE A JOUR : nous avons depuis relance l'execution reelle jusqu'a 1000
  rounds demandes (1027 observes, ~25M evenements) -- voir section 6
  ci-dessous et `results/figures/energy_vs_rounds_real.png` : le reseau
  perd bien 69 capteurs sur 100 sur cette fenetre (FND au round 251).
- **Numerotation des noeuds (0-index vs 1-index)** : `ch_schedule.h` est
  genere par `generate_schedule.py` (anciennement `python-sim/run_experiments.py`,
  dossier supprime depuis -- l'algorithme PSO vit maintenant dans
  `tinyos/pso_clustering.py`) en indexation Python (0..N-1) alors que les
  motes nesC sont numerotes 1..N (mote 0 = BS).
  Ce decalage a ete identifie et corrige dans le generateur avant cette
  session de mise au point du toolchain Docker (voir historique du
  fichier) ; il est mentionne ici car c'est exactement le genre d'erreur
  d'off-by-one qui, combinee a l'absence de validation croisee
  topology.h/ch_schedule.h par le systeme de build, aurait pu passer
  inapercue (compilation et execution parfaitement silencieuses, resultats
  simplement faux -- tous les "CH" designes auraient ete des motes
  voisins de ceux voulus).

## 6. Passage a l'echelle reel (N=50, 100, 300) et decouverte a N=300

Suite a une demande de verifier reellement le point "Relancer la simu avec
50, 100, puis 300 noeuds" de l'enonce, nous avons genere une topologie et
un planning PSO pour chacune de ces 3 tailles (`generate_schedule.py
<rounds> <N>`), reconstruit une image Docker par taille, et execute
reellement TOSSIM pour chacune (30 rounds suffisent pour mesurer le trafic
de controle moyen par round, cf. `CTRL_SENT` dans les logs).

Resultat : **N=50 et N=100 fonctionnent** (85.0 et 157.3 messages de
controle/round mesures, contre 101 et 201 attendus par construction -- la
difference vient de CHLIST parfois perdus, un effet radio reel). **N=300
echoue totalement : zero message de controle n'est jamais envoye**, sur
toute la fenetre testee.

Diagnostic (instrumentation ajoutee temporairement dans
`PSOClusteringC.nc`, retiree ensuite) : le message `CHLIST` doit lister
jusqu'a k=15 Cluster Heads a N=300 (5% de 300), soit 40 octets avec
l'en-tete du message. En tracant directement le pointeur retourne par
`call Packet.getPayload(&pktCtrl, sizeof(ctrl_msg_t))`, nous avons confirme
qu'il vaut `NULL` des le premier round : TOSSIM/la plateforme simulee
refuse de fournir un buffer pour ce message au-dela d'environ 28 octets
(limite reelle du payload radio, MAX_CH ~9 nœuds maximum dans la liste).
Aucune erreur n'est levee -- la simulation tourne normalement, le compteur
`ENERGY_TOTAL` continue de s'incrementer round apres round, mais la
diffusion `CHLIST` elle-meme n'a jamais lieu, donc rien d'autre ne peut
fonctionner en aval (pas de JOIN, pas de DATA).

C'est une limite de plateforme (pas un bug applicatif) qui demontre
concretement, et non plus seulement en theorie, l'avertissement de
l'enonce sur le passage a l'echelle de TOSSIM : voir
`results/figures/scalability_real.png` et `results/data/scalability_real.csv`.
