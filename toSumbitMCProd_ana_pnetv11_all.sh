#!/bin/bash
# CutBasedDM histogramming with the v11 ParticleNet, into analysis_pnetv11/.
#
# ParticleNet dominates the cost, so files per task is set per sample to keep
# every task near 25 min. Events per file differ by a factor of 10 between
# samples, so one global -f would give either 3 min tasks or 14 h ones, and the
# long ones get killed by preemption.
#
# Measured on one ecal_pn file: 9315 events in 5:13, so 34 ms/event and 1.0 GB
# peak RSS. Faster than the 65 ms of v10 because v11 skips untracked events.
#
#   sample                ev/file   files/task   min/task
#   ecal_pn                  8.7k       5           24
#   ecal_conversion         39.9k       1           22
#   target_pn                8.3k       5           23
#   target_conversion       10.9k       4           24
#   signal (any mass)       ~81k       1           45+
#
# Signal is the slow one per event: nearly every event has a recoil track, so
# ParticleNet actually runs, where in ecal_pn many events are skipped.
#
# Chunk sizes must not change once a sample has started: the histogram is named
# after the LAST file of the chunk, so a different -f silently overwrites the
# output of another chunk and drops its files.
CFG=cfg_ana_cutBasedDM_pnetv11.py
BASE=/sdf/data/ldmx/private_production/mc26/reco_v492
NPAR=${NPAR:-16}
SLEEP=${SLEEP:-8}
MEM=${MEM:-4000}   # measured peak is 1.0 GB per task
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

# --tag is anav11_* so the skip logic does not see the v10 run's filelists
for m in $MASSES ; do
  python3 ../submit_sdf_mt_input.py -py $CFG -i $BASE/signal_v15_8gev/$m \
    -f 1 -n $NPAR -s $SLEEP -m $MEM --pattern '*_reco.root' --tag anav11_signal_$m "$@"
done

for s in $SAMPLES ; do
  python3 ../submit_sdf_mt_input.py -py $CFG -i $BASE/$s \
    -f $(files_per_task $s) -n $NPAR -s $SLEEP -m $MEM --pattern '*_reco.root' \
    --tag anav11_$s "$@"
done
