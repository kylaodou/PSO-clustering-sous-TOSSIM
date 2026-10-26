// PSOClusteringAppC.nc -- branche PSOClusteringC aux composants TinyOS (radio, timers).
#include "PSOClustering.h"

configuration PSOClusteringAppC { }
implementation {
  components MainC;
  components PSOClusteringC as App;
  components ActiveMessageC;
  components new AMSenderC(AM_CTRLMSG) as CtrlSenderC;
  components new AMReceiverC(AM_CTRLMSG) as CtrlReceiverC;
  components new AMSenderC(AM_DATAMSG) as DataSenderC;
  components new AMReceiverC(AM_DATAMSG) as DataReceiverC;
  components new TimerMilliC() as PhaseTimerC;
  components new TimerMilliC() as JitterTimerC;
  components RandomC;

  App.Boot -> MainC;
  App.AMControl -> ActiveMessageC;
  App.Packet -> CtrlSenderC;

  App.CtrlSend -> CtrlSenderC;
  App.CtrlReceive -> CtrlReceiverC;
  App.DataSend -> DataSenderC;
  App.DataReceive -> DataReceiverC;

  App.PhaseTimer -> PhaseTimerC;
  App.JitterTimer -> JitterTimerC;
  App.Random -> RandomC;
}
