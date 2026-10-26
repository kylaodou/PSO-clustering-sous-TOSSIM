// PSOClusteringC.nc -- comportement d'un mote (capteur ou BS) du protocole
// PSO-clustering : collecte d'energie, election des CH, TDMA, remontee des donnees.

#include "PSOClustering.h"
#include <math.h>

module PSOClusteringC {
  uses {
    interface Boot;
    interface SplitControl as AMControl;
    interface AMSend as CtrlSend;
    interface Receive as CtrlReceive;
    interface AMSend as DataSend;
    interface Receive as DataReceive;
    interface Packet;
    interface Timer<TMilli> as PhaseTimer;
    interface Timer<TMilli> as JitterTimer;
    interface Random;
  }
}
implementation {

  message_t pktCtrl;
  message_t pktData;
  bool ctrlBusy = FALSE;
  bool dataBusy = FALSE;

  uint16_t myId;
  int16_t myX, myY;
  float residualEnergy;
  bool alive;
  uint16_t currentRound;
  uint8_t phase;

  bool isCH;
  uint16_t myCH;

  uint16_t lastChList[MAX_CH];
  uint8_t lastChListCount;

  uint16_t memberIds[NUM_NODES];
  uint8_t memberCount;
  uint8_t membersReportedThisRound;

  uint16_t dataSeq;

  // BS uniquement : accumulateurs remis a zero a chaque round.
  float bsEnergyReportSum;
  uint16_t bsEnergyReportCount;
  uint32_t bsDataDelivered;

  // ---- fonctions utilitaires (position, distance, cout energetique) ----

  void getPos(uint16_t id, int16_t* x, int16_t* y) {
    if (id == 0) { *x = BS_X_CM; *y = BS_Y_CM; return; }
    if (id >= 1 && id <= NUM_NODES) {
      *x = node_pos_cm[id - 1][0];
      *y = node_pos_cm[id - 1][1];
    } else {
      *x = 0; *y = 0;
    }
  }

  float distanceM(int16_t x1cm, int16_t y1cm, int16_t x2cm, int16_t y2cm) {
    float dx = (x1cm - x2cm) / 100.0f;
    float dy = (y1cm - y2cm) / 100.0f;
    return sqrtf(dx * dx + dy * dy);
  }

  // Modele radio de premier ordre (seuil de distance RADIO_D0_M, cf. PSOClustering.h).
  float txEnergy(uint16_t bits, float distance) {
    if (distance < RADIO_D0_M) {
      return bits * E_ELEC_J_PER_BIT + bits * E_FS_J_PER_BIT_M2 * distance * distance;
    }
    return bits * E_ELEC_J_PER_BIT
         + bits * E_MP_J_PER_BIT_M4 * distance * distance * distance * distance;
  }

  float rxEnergy(uint16_t bits) {
    return bits * E_ELEC_J_PER_BIT;
  }

  float aggEnergy(float bits) {
    return bits * E_DA_J_PER_BIT;
  }

  // Deduit l'energie d'une operation radio ; declare le noeud mort si elle tombe a 0.
  void deductEnergy(float e) {
    if (myId == 0) return; // BS non contrainte en energie, cf. rapport
    residualEnergy -= e;
    if (residualEnergy <= 0.0f) {
      residualEnergy = 0.0f;
      if (alive) {
        alive = FALSE;
        dbg("PSO", "DEAD,%hu,%hu\n", myId, currentRound);
      }
    }
  }

  uint32_t jitter(uint32_t windowMs) {
    if (windowMs == 0) return 0;
    return (call Random.rand16()) % windowMs;
  }

  // Charge le planning PSO precalcule (ch_schedule.h) pour ce round.
  void loadChScheduleForRound(uint16_t round) {
    uint16_t r = round % NUM_DEMO_ROUNDS;
    uint8_t i;
    lastChListCount = ch_schedule_count[r];
    if (lastChListCount > MAX_CH) lastChListCount = MAX_CH;
    for (i = 0; i < lastChListCount; i++) {
      lastChList[i] = ch_schedule[r][i];
    }
  }

  // Cote capteur : suis-je CH ? sinon, quel CH annonce est le plus proche ?
  void decideRoleFromChList() {
    uint8_t i;
    uint16_t bestCh;
    float bestDist, d;
    int16_t cx, cy;

    isCH = FALSE;
    myCH = 0xFFFF;

    for (i = 0; i < lastChListCount; i++) {
      if (lastChList[i] == myId) {
        isCH = TRUE;
        myCH = myId;
        return;
      }
    }
    if (lastChListCount == 0) {
      return; // CHLIST perdue ce round : le noeud reste inactif
    }
    bestCh = 0xFFFF;
    bestDist = 1.0e30f;
    for (i = 0; i < lastChListCount; i++) {
      getPos(lastChList[i], &cx, &cy);
      d = distanceM(myX, myY, cx, cy);
      if (d < bestDist) {
        bestDist = d;
        bestCh = lastChList[i];
      }
    }
    myCH = bestCh;
  }

  // ---- emission des messages (1 fonction par type de message) ----

  // Capteur -> BS : remonte l'energie residuelle (phase PH_INFO).
  void sendInfo() {
    ctrl_msg_t* m;
    float d;
    if (ctrlBusy) return;
    d = distanceM(myX, myY, BS_X_CM, BS_Y_CM);
    deductEnergy(txEnergy(CTRL_PACKET_BITS, d));
    if (!alive) return;
    m = (ctrl_msg_t*)(call Packet.getPayload(&pktCtrl, sizeof(ctrl_msg_t)));
    if (m == NULL) return;
    m->type = CTRL_TYPE_INFO;
    m->srcId = myId;
    m->dstId = 0;
    m->energy_uj = (uint32_t)(residualEnergy * 1000000.0f);
    m->numCh = 0;
    if (call CtrlSend.send(AM_BROADCAST_ADDR, &pktCtrl, sizeof(ctrl_msg_t)) == SUCCESS) {
      ctrlBusy = TRUE;
      dbg("PSO", "CTRL_SENT,%hu,%hhu\n", currentRound, (uint8_t)CTRL_TYPE_INFO);
    }
  }

  // BS -> tous : diffuse la liste des CH du round (planning precalcule).
  // Limite mesuree : au-dela de ~28 octets (MAX_CH ~9), getPayload() refuse le message.
  void sendChListBroadcast() {
    ctrl_msg_t* m;
    uint8_t i;
    if (ctrlBusy) return;
    m = (ctrl_msg_t*)(call Packet.getPayload(&pktCtrl, sizeof(ctrl_msg_t)));
    if (m == NULL) return;
    m->type = CTRL_TYPE_CHLIST;
    m->srcId = 0;
    m->dstId = 0xFFFF;
    m->energy_uj = 0;
    m->numCh = lastChListCount;
    for (i = 0; i < lastChListCount; i++) {
      m->chIds[i] = lastChList[i];
    }
    if (call CtrlSend.send(AM_BROADCAST_ADDR, &pktCtrl, sizeof(ctrl_msg_t)) == SUCCESS) {
      ctrlBusy = TRUE;
      dbg("PSO", "CTRL_SENT,%hu,%hhu\n", currentRound, (uint8_t)CTRL_TYPE_CHLIST);
    }
  }

  // Membre -> son CH : demande d'adhesion au cluster.
  void sendJoin() {
    ctrl_msg_t* m;
    int16_t cx, cy;
    float d;
    if (ctrlBusy || myCH == 0xFFFF) return;
    getPos(myCH, &cx, &cy);
    d = distanceM(myX, myY, cx, cy);
    deductEnergy(txEnergy(CTRL_PACKET_BITS, d));
    if (!alive) return;
    m = (ctrl_msg_t*)(call Packet.getPayload(&pktCtrl, sizeof(ctrl_msg_t)));
    if (m == NULL) return;
    m->type = CTRL_TYPE_JOIN;
    m->srcId = myId;
    m->dstId = myCH;
    m->energy_uj = 0;
    m->numCh = 0;
    if (call CtrlSend.send(AM_BROADCAST_ADDR, &pktCtrl, sizeof(ctrl_msg_t)) == SUCCESS) {
      ctrlBusy = TRUE;
      dbg("PSO", "CTRL_SENT,%hu,%hhu\n", currentRound, (uint8_t)CTRL_TYPE_JOIN);
    }
  }

  // CH -> ses membres : synchronisation (pas de contenu, cf. rapport pour le detail TDMA/CSMA).
  void sendSchedBroadcast() {
    ctrl_msg_t* m;
    uint8_t i;
    float maxDist, d;
    int16_t px, py;
    if (ctrlBusy) return;
    maxDist = 1.0f;
    for (i = 0; i < memberCount; i++) {
      getPos(memberIds[i], &px, &py);
      d = distanceM(myX, myY, px, py);
      if (d > maxDist) maxDist = d;
    }
    deductEnergy(txEnergy(CTRL_PACKET_BITS, maxDist));
    if (!alive) return;
    m = (ctrl_msg_t*)(call Packet.getPayload(&pktCtrl, sizeof(ctrl_msg_t)));
    if (m == NULL) return;
    m->type = CTRL_TYPE_SCHED;
    m->srcId = myId;
    m->dstId = 0xFFFF;
    m->energy_uj = 0;
    m->numCh = 0;
    if (call CtrlSend.send(AM_BROADCAST_ADDR, &pktCtrl, sizeof(ctrl_msg_t)) == SUCCESS) {
      ctrlBusy = TRUE;
      dbg("PSO", "CTRL_SENT,%hu,%hhu\n", currentRound, (uint8_t)CTRL_TYPE_SCHED);
    }
  }

  // Membre -> son CH : 1 mesure par round (phase PH_DATA).
  void sendData() {
    data_msg_t* m;
    int16_t cx, cy;
    float d;
    if (dataBusy || myCH == 0xFFFF) return;
    getPos(myCH, &cx, &cy);
    d = distanceM(myX, myY, cx, cy);
    deductEnergy(txEnergy(DATA_PACKET_BITS, d));
    if (!alive) return;
    m = (data_msg_t*)(call Packet.getPayload(&pktData, sizeof(data_msg_t)));
    if (m == NULL) return;
    m->type = DATA_TYPE_SENSOR_TO_CH;
    m->srcId = myId;
    m->dstId = myCH;
    m->seq = dataSeq++;
    m->numAggregated = 0;
    if (call DataSend.send(AM_BROADCAST_ADDR, &pktData, sizeof(data_msg_t)) == SUCCESS) {
      dataBusy = TRUE;
      dbg("PSO", "DATA_ATTEMPT,%hu,%hu\n", currentRound, myId);
    }
  }

  // CH -> BS : agrege les mesures recues des membres puis relaie a la BS.
  void sendDataToBs() {
    data_msg_t* m;
    float d;
    uint8_t totalReports;
    if (dataBusy) return;
    totalReports = membersReportedThisRound + 1; // +1 : la propre lecture du CH
    if (membersReportedThisRound > 0) {
      deductEnergy(aggEnergy((float)DATA_PACKET_BITS * membersReportedThisRound));
    }
    d = distanceM(myX, myY, BS_X_CM, BS_Y_CM);
    deductEnergy(txEnergy(DATA_PACKET_BITS, d));
    if (!alive) return;
    m = (data_msg_t*)(call Packet.getPayload(&pktData, sizeof(data_msg_t)));
    if (m == NULL) return;
    m->type = DATA_TYPE_CH_TO_BS;
    m->srcId = myId;
    m->dstId = 0;
    m->seq = dataSeq++;
    m->numAggregated = totalReports;
    if (call DataSend.send(AM_BROADCAST_ADDR, &pktData, sizeof(data_msg_t)) == SUCCESS) {
      dataBusy = TRUE;
      dbg("PSO", "DATA_ATTEMPT,%hu,%hu\n", currentRound, myId);
    }
  }

  // ---- demarrage et machine a etats (1 timer de phase par round) ----

  event void Boot.booted() {
    myId = TOS_NODE_ID;
    currentRound = 0;
    phase = PH_INFO;
    isCH = FALSE;
    myCH = 0xFFFF;
    lastChListCount = 0;
    memberCount = 0;
    membersReportedThisRound = 0;
    dataSeq = 0;
    bsEnergyReportSum = 0.0f;
    bsEnergyReportCount = 0;
    bsDataDelivered = 0;

    if (myId == 0) {
      myX = BS_X_CM;
      myY = BS_Y_CM;
      alive = TRUE;
    } else {
      getPos(myId, &myX, &myY);
      residualEnergy = E_INIT_J;
      alive = TRUE;
    }
    call AMControl.start();
  }

  event void AMControl.startDone(error_t err) {
    if (err != SUCCESS) {
      call AMControl.start();
      return;
    }
    dbg("PSO", "BOOT,%hu,%d,%d\n", myId, (int)myX, (int)myY);
    call PhaseTimer.startOneShot(PHASE_INFO_MS);
    if (myId != 0 && alive) {
      call JitterTimer.startOneShot(jitter(PHASE_INFO_MS));
    }
  }

  event void AMControl.stopDone(error_t err) { }

  // Avance d'une phase a chaque declenchement ; boucle PH_INFO -> ... -> PH_DATA -> PH_INFO.
  event void PhaseTimer.fired() {
    switch (phase) {

      case PH_INFO:
        if (myId == 0) {
          loadChScheduleForRound(currentRound);
          sendChListBroadcast();
          dbg("PSO", "ENERGY_TOTAL,%hu,%lu\n", currentRound,
              (uint32_t)(bsEnergyReportSum * 1000.0f));
          bsEnergyReportSum = 0.0f;
          bsEnergyReportCount = 0;
        }
        phase = PH_CHLIST;
        call PhaseTimer.startOneShot(PHASE_CHLIST_MS);
        break;

      case PH_CHLIST:
        if (myId != 0 && alive) {
          decideRoleFromChList();
          if (!isCH && myCH != 0xFFFF) {
            call JitterTimer.startOneShot(jitter(PHASE_JOIN_MS));
          }
        }
        phase = PH_JOIN;
        call PhaseTimer.startOneShot(PHASE_JOIN_MS);
        break;

      case PH_JOIN:
        if (myId != 0 && alive && isCH) {
          sendSchedBroadcast();
        }
        phase = PH_SCHED;
        call PhaseTimer.startOneShot(PHASE_SCHED_MS);
        break;

      case PH_SCHED:
        if (myId != 0 && alive && !isCH && myCH != 0xFFFF) {
          call JitterTimer.startOneShot(jitter(PHASE_DATA_MS));
        }
        phase = PH_DATA;
        call PhaseTimer.startOneShot(PHASE_DATA_MS);
        break;

      case PH_DATA:
      default:
        if (myId != 0 && alive && isCH) {
          sendDataToBs();
        }
        dbg("PSO", "ROUND_END,%hu,%hu,%hhu\n", currentRound, myId, isCH ? 1 : 0);

        isCH = FALSE;
        myCH = 0xFFFF;
        lastChListCount = 0;
        memberCount = 0;
        membersReportedThisRound = 0;

        currentRound++;
        phase = PH_INFO;
        if (myId != 0 && alive) {
          call JitterTimer.startOneShot(jitter(PHASE_INFO_MS));
        }
        call PhaseTimer.startOneShot(PHASE_INFO_MS);
        break;
    }
  }

  // Declenche l'envoi propre a la phase courante, a un instant aleatoire dans la fenetre.
  event void JitterTimer.fired() {
    if (!alive) return;
    switch (phase) {
      case PH_INFO:
        sendInfo();
        break;
      case PH_JOIN:
        if (!isCH) sendJoin();
        break;
      case PH_DATA:
        if (!isCH) sendData();
        break;
      default:
        break;
    }
  }

  // ---- reception des messages ----

  event message_t* CtrlReceive.receive(message_t* msg, void* payload, uint8_t len) {
    ctrl_msg_t* m = (ctrl_msg_t*)payload;
    uint8_t i;
    if (len < sizeof(ctrl_msg_t)) return msg;

    if (m->type == CTRL_TYPE_INFO) {
      if (myId == 0) {
        bsEnergyReportSum += ((float)m->energy_uj) / 1000000.0f;
        bsEnergyReportCount++;
      }
    } else if (m->type == CTRL_TYPE_CHLIST) {
      if (myId != 0) {
        lastChListCount = m->numCh;
        if (lastChListCount > MAX_CH) lastChListCount = MAX_CH;
        for (i = 0; i < lastChListCount; i++) {
          lastChList[i] = m->chIds[i];
        }
      }
    } else if (m->type == CTRL_TYPE_JOIN) {
      if (myId != 0 && isCH && m->dstId == myId) {
        if (memberCount < NUM_NODES) {
          memberIds[memberCount++] = m->srcId;
        }
        deductEnergy(rxEnergy(CTRL_PACKET_BITS));
      }
    }
    // CTRL_TYPE_SCHED : synchronisation implicite, rien a traiter ici.
    return msg;
  }

  event void CtrlSend.sendDone(message_t* msg, error_t err) {
    ctrlBusy = FALSE;
  }

  event message_t* DataReceive.receive(message_t* msg, void* payload, uint8_t len) {
    data_msg_t* m = (data_msg_t*)payload;
    if (len < sizeof(data_msg_t)) return msg;

    // Un broadcast est recu par tous les motes a portee : ce filtre evite
    // qu'un capteur soit compte par plusieurs CH concurrents a la fois.
    if (m->type == DATA_TYPE_SENSOR_TO_CH) {
      if (myId != 0 && isCH && m->dstId == myId) {
        deductEnergy(rxEnergy(DATA_PACKET_BITS));
        membersReportedThisRound++;
        dbg("PSO", "DATA_HOP1,%hu,%hu,%hu\n", currentRound, m->srcId, myId);
      }
    } else {
      if (myId == 0) {
        bsDataDelivered += m->numAggregated;
        dbg("PSO", "DATA_BS,%hu,%hu,%hhu\n", currentRound, m->srcId, m->numAggregated);
      }
    }
    return msg;
  }

  event void DataSend.sendDone(message_t* msg, error_t err) {
    dataBusy = FALSE;
  }
}
