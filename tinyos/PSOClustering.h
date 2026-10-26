// PSOClustering.h -- constantes, structures de messages et modele radio.
// Mote 0 = BS (voir rapport) ; motes 1..NUM_NODES = capteurs (topology.h).

#ifndef PSOCLUSTERING_H
#define PSOCLUSTERING_H

#include "topology.h"
#include "ch_schedule.h"

// Modele radio de premier ordre. E_MP corrige en pJ (l'enonce donne nJ,
// incoherent avec le scenario) -- voir rapport, section Methodologie.
#define E_ELEC_J_PER_BIT     50.0e-9f
#define E_FS_J_PER_BIT_M2    10.0e-12f
#define E_MP_J_PER_BIT_M4    1.3e-15f
#define E_DA_J_PER_BIT       5.0e-9f
#define RADIO_D0_M           87.7f

#define E_INIT_J             0.5f

#define DATA_PACKET_BITS     4000
#define CTRL_PACKET_BITS     200

// Duree des phases d'un round (ms) ; somme = duree totale d'un round.
#define PHASE_INFO_MS        500
#define PHASE_CHLIST_MS      200
#define PHASE_JOIN_MS        500
#define PHASE_SCHED_MS       200
#define PHASE_DATA_MS        1000

#define AM_CTRLMSG   10
#define AM_DATAMSG   11

enum {
  CTRL_TYPE_INFO   = 0,
  CTRL_TYPE_CHLIST = 1,
  CTRL_TYPE_JOIN   = 2,
  CTRL_TYPE_SCHED  = 3,
};

enum {
  DATA_TYPE_SENSOR_TO_CH = 0,
  DATA_TYPE_CH_TO_BS     = 1,
};

enum {
  PH_INFO   = 0,
  PH_CHLIST = 1,
  PH_JOIN   = 2,
  PH_SCHED  = 3,
  PH_DATA   = 4,
};

// dstId : id du CH vise (JOIN) ; chIds/numCh : valides seulement pour CHLIST.
typedef nx_struct ctrl_msg {
  nx_uint8_t  type;
  nx_uint16_t srcId;
  nx_uint16_t dstId;
  nx_uint32_t energy_uj;
  nx_uint8_t  numCh;
  nx_uint16_t chIds[MAX_CH];
} ctrl_msg_t;

// numAggregated : nombre de mesures agregees, valide seulement pour CH_TO_BS.
typedef nx_struct data_msg {
  nx_uint8_t  type;
  nx_uint16_t srcId;
  nx_uint16_t dstId;
  nx_uint16_t seq;
  nx_uint8_t  numAggregated;
} data_msg_t;

#endif // PSOCLUSTERING_H
