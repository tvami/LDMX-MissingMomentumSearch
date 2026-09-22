#!/bin/bash
# Cutflow histogramming with the Humberto BDT re-run in the analysis job.
# One input file per task (files are 11k-94k events each).
CFG=cfg_ana_cutBasedDM_v15_humbertoBDT.py
BASE=/sdf/data/ldmx/private_production/mc26/reco_dropsim

for s in ecal_conversion_v15_8gev ecal_pn_v15_8gev target_pn_v15_8gev target_conversion_v15_8gev ; do
  python3 submit_sdf_mt_input.py -py $CFG -i $BASE/$s -f 1 --no-skip
done

for m in 1.0 0.1 0.01 0.001 ; do
  python3 submit_sdf_mt_input.py -py $CFG -i $BASE/signal_v15_8gev/$m -f 1 --no-skip
done
