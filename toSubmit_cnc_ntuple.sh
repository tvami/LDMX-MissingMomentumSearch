#!/bin/bash
# CnC ntuple campaign (PLAN_CNC_PUNZI.md) into ntuple_cnc/.
# 20 files per task for backgrounds, 1 for signal, so chunk names match analysis/.
# Job names cnc_*, filelist tags cncnt_*, so drains can tell the campaigns apart.
CFG=cfg_ntuple_cnc.py
BASE=/sdf/data/ldmx/private_production/mc26/reco_v492
NPAR=${NPAR:-16}
MEM=${MEM:-3000}

for m in 1.0 0.1 0.01 0.001 ; do
  python3 ../submit_sdf_mt_input.py -py $CFG -i $BASE/signal_v15_8gev/$m \
    -f 1 -n $NPAR -s 5 -m $MEM --pattern '*_reco.root' \
    --tag cncnt_signal_$m --jobname cnc_sig_$m "$@"
done

for s in ecal_pn ecal_conversion target_pn target_conversion ; do
  python3 ../submit_sdf_mt_input.py -py $CFG -i $BASE/${s}_v15_8gev \
    -f 20 -n $NPAR -s 5 -m $MEM --pattern '*_reco.root' \
    --tag cncnt_$s --jobname cnc_$s "$@"
done
