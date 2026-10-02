#!/bin/bash
# Re-run ECal PN and the four signal masses with the extra histograms, into
# analysis_nhits/.
#
# Only these five samples: the other three backgrounds are already below one
# event, and the questions this answers are about the ECal PN yield and the
# signal efficiency at a tighter ParticleNet cut.
#
# Same files per task as before, so the chunk names line up with the earlier run
# and the two trees can be compared chunk by chunk.
CFG=cfg_ana_cutBasedDM_nhits.py
BASE=/sdf/data/ldmx/private_production/mc26/reco_v492
NPAR=${NPAR:-16}
SLEEP=${SLEEP:-8}
MEM=${MEM:-4000}
MASSES=${MASSES-"1.0 0.1 0.01 0.001"}

for m in $MASSES ; do
  python3 ../submit_sdf_mt_input.py -py $CFG -i $BASE/signal_v15_8gev/$m \
    -f 1 -n $NPAR -s $SLEEP -m $MEM --pattern '*_reco.root' --tag anhits_signal_$m "$@"
done

python3 ../submit_sdf_mt_input.py -py $CFG -i $BASE/ecal_pn_v15_8gev \
  -f 5 -n $NPAR -s $SLEEP -m $MEM --pattern '*_reco.root' --tag anhits_ecal_pn "$@"
