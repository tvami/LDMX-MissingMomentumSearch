#!/bin/bash
# All eight samples into analysis_notrk/: the aligned flows plus the same flows
# without the tracker veto (BDTNoTrk, PNetNoTrk; CnC needs no new flow).
#
# Files per task as in the v11 campaign, ~25 min per task with ParticleNet.
# Jobs are named ntk_* so drains can tell this campaign apart.
CFG=cfg_ana_cutBasedDM_notrk.py
BASE=/sdf/data/ldmx/private_production/mc26/reco_v492
NPAR=${NPAR:-16}
SLEEP=${SLEEP:-8}
MEM=${MEM:-4000}
MASSES=${MASSES-"1.0 0.1 0.01 0.001"}
SAMPLES=${SAMPLES-"target_pn_v15_8gev target_conversion_v15_8gev ecal_conversion_v15_8gev ecal_pn_v15_8gev"}

files_per_task () {
  case $1 in
    ecal_pn_v15_8gev)           echo 5 ;;
    ecal_conversion_v15_8gev)   echo 1 ;;
    target_pn_v15_8gev)         echo 5 ;;
    target_conversion_v15_8gev) echo 4 ;;
    *)                          echo 1 ;;
  esac
}

for m in $MASSES ; do
  python3 ../submit_sdf_mt_input.py -py $CFG -i $BASE/signal_v15_8gev/$m \
    -f 1 -n $NPAR -s $SLEEP -m $MEM --pattern '*_reco.root' \
    --tag ntk_signal_$m --jobname ntk_sig$m "$@"
done

for s in $SAMPLES ; do
  python3 ../submit_sdf_mt_input.py -py $CFG -i $BASE/$s \
    -f $(files_per_task $s) -n $NPAR -s $SLEEP -m $MEM --pattern '*_reco.root' \
    --tag ntk_$s --jobname ntk_${s%_v15_8gev} "$@"
done
