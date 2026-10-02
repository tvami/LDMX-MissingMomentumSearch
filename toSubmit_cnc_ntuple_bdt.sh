#!/bin/bash
# CnC ntuple with the tracker veto branch, into ntuple_cnc_bdt/, with the BDT score.
# 20 files per task for backgrounds, 1 for signal, so chunk names match analysis/.
# Job names cnc_trk_*, filelist tags cnctrk_*; drains that skip cnc_* ignore them.
CFG=cfg_ntuple_cnc_bdt.py
BASE=/sdf/data/ldmx/private_production/mc26/reco_v492
NPAR=${NPAR:-16}
MEM=${MEM:-3000}

for m in 1.0 0.1 0.01 0.001 ; do
  python3 ../submit_sdf_mt_input.py -py $CFG -i $BASE/signal_v15_8gev/$m \
    -f 1 -n $NPAR -s 5 -m $MEM --pattern '*_reco.root' \
    --tag cncbdt_signal_$m --jobname cnc_bdt_sig_$m "$@"
done

for s in ecal_pn ecal_conversion target_pn target_conversion ; do
  python3 ../submit_sdf_mt_input.py -py $CFG -i $BASE/${s}_v15_8gev \
    -f 20 -n $NPAR -s 5 -m $MEM --pattern '*_reco.root' \
    --tag cncbdt_$s --jobname cnc_bdt_$s "$@"
done
