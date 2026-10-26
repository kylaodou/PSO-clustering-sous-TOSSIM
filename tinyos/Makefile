# Makefile TinyOS/TOSSIM pour l'application PSOClustering.
#
# Utilisation (depuis un environnement TinyOS 2.1.2 fonctionnel, avec
# TOSROOT/TOSDIR/PATH correctement exportes) :
#
#   make micaz sim      # compile PSOClusteringAppC.py / _TOSSIM.so pour TOSSIM
#
# La plateforme "micaz" est choisie car c'est la cible historique de
# reference de TOSSIM (4 Ko RAM / 128 Ko flash) ; voir le rapport pour la
# discussion sur l'impact de cette contrainte RAM sur l'architecture
# (calcul PSO precalcule hors-ligne plutot qu'embarque).
#
# math.h / sqrtf() necessite de lier libm.

COMPONENT=PSOClusteringAppC
LIBS += -lm

# NOTE (correction toolchain, cf. README.md / Journal technique) : le Makefile TinyOS 2.0
# historique utilisait `include $(MAKERULES)` (variable TOSROOT/TOSDIR/
# MAKERULES). Le systeme de build de tinyos-main (>= 2.1) a deprecie ce
# mecanisme au profit de TINYOS_ROOT_DIR + Makefile.include (cf.
# support/make/README.md). On garde `?=` pour permettre un environnement qui
# exporterait deja TINYOS_ROOT_DIR (c'est le cas dans l'image Docker finale).
TINYOS_ROOT_DIR?=/opt/tinyos-main
include $(TINYOS_ROOT_DIR)/Makefile.include
