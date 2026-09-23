#!/bin/bash
# CutBasedDM histogramming over the v4.9.2 reco. The veto there is already the
# Humberto BDT, so the analyzer reads it from the reco pass and nothing is re-run.
#
# 40 files per task: the analyzer is ~10 s per reco file, so one file per task
# would be all scheduler overhead.
CFG=cfg_ana_cutBasedDM_v492.py
BASE=/sdf/data/ldmx/private_production/mc26/reco_v492
NPAR=${NPAR:-16}
SLEEP=${SLEEP:-20}
MEM=${MEM:-8000}
MASSES=${MASSES-"1.0 0.1 0.01 0.001"}
SAMPLES=${SAMPLES-"target_pn_v15_8gev target_conversion_v15_8gev ecal_conversion_v15_8gev ecal_pn_v15_8gev"}

for m in $MASSES ; do
  python3 ../submit_sdf_mt_input.py -py $CFG -i $BASE/signal_v15_8gev/$m \
    -f 10 -n $NPAR -s $SLEEP -m $MEM --pattern '*_reco.root' --tag ana492_signal_$m "$@"
done

for s in $SAMPLES ; do
  python3 ../submit_sdf_mt_input.py -py $CFG -i $BASE/$s \
    -f 20 -n $NPAR -s $SLEEP -m $MEM --pattern '*_reco.root' --tag ana492_$s "$@"
done
