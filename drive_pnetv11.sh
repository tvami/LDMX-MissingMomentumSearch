#!/bin/bash
# Drive the v11 ParticleNet campaign to completion: wait, recover, hadd, tabulate.
#
# Preemption on this QOS cancels tasks mid-run, so a single submission never
# finishes the whole sample. Each round re-checks which chunks have no usable
# histogram and resubmits exactly those, up to MAXROUND times, then merges.
#
# A histogram counts as usable only if it actually holds histograms:
# a killed job leaves a ~500 byte file that exists and is non-empty but has no
# keys, because histograms are only written at close.
export PATH=/sdf/home/t/tamasvami/.local/bin:$PATH
D=/sdf/group/ldmx/users/tamasvami/ldmx-analysis/v4.9.2/ldmx-sw
M=$D/LDMX-MissingMomentumSearch
SO=$D/scan_out
LOG=$SO/drive_pnetv11.log
G=/sdf/group/ldmx/users/tamasvami/slurm
CFG=cfg_ana_cutBasedDM_pnetv11.py
MAXROUND=${MAXROUND:-4}
# The python scripts take the tree as "--ana", not as an env var: denv runs them
# inside the container with denv_env_var_copy_all="false", so an exported
# ANA_DIR never arrives and they silently fall back to analysis/. That happened
# and reported the v10 tree's 297 chunks as this run's progress.
ANA=analysis_pnetv11
# hadd_v492.sh is host bash, so the variable does reach it
export ANA_DIR=$ANA
mkdir -p $G/jobs $G/logs $G/filelists
cd $M || exit 1

# sample:files_per_task, must match toSumbitMCProd_ana_pnetv11_all.sh
SF="ecal_pn_v15_8gev:5 ecal_conversion_v15_8gev:1 target_pn_v15_8gev:5
    target_conversion_v15_8gev:4 signal_v15_8gev/1.0:1 signal_v15_8gev/0.1:1
    signal_v15_8gev/0.01:1 signal_v15_8gev/0.001:1"

drain () {
  while true; do
    Q=$(squeue -u tamasvami -h -t R,PD -o '%i %r' 2>/dev/null \
        | awk '$2 != "JobHeldUser"' | grep -c .)
    [ "$Q" -eq 0 ] && break
    sleep 120
  done
}

echo "$(date '+%F %T') driver start" > $LOG

for round in $(seq 1 $MAXROUND); do
  echo "$(date '+%F %T') round $round: waiting for drain" >> $LOG
  drain
  echo "$(date '+%F %T') round $round: drained, checking" >> $LOG

  : > /tmp/v11_missing.txt
  for sf in $SF ; do
    s=${sf%:*}; f=${sf#*:}
    tag=$(echo $s | tr '/' '_')
    denv python3 prune_strays.py --ana $ANA $s $f --apply >> $LOG 2>&1
    denv python3 find_missing_chunks.py --ana $ANA $s $f $G/filelists/v11rec_$tag \
      >> /tmp/v11_missing.txt 2>>$LOG
  done
  N=$(grep -c . /tmp/v11_missing.txt)
  echo "$(date '+%F %T') round $round: $N chunks missing" >> $LOG
  [ "$N" -eq 0 ] && break

  # 16 tasks per job, one node each, same shape as the main submission
  rm -f /tmp/v11g_*
  split -l 16 -d -a 4 /tmp/v11_missing.txt /tmp/v11g_
  for g in /tmp/v11g_* ; do
    n=$(grep -c . $g)
    JF=$G/jobs/v11rec_r${round}_$(basename $g).job
    {
      echo '#!/bin/bash'
      echo "#SBATCH --partition=roma"
      echo "#SBATCH --account=ldmx"
      echo "#SBATCH --nodes=1"
      echo "#SBATCH --ntasks=$n"
      echo "#SBATCH --cpus-per-task=1"
      echo "#SBATCH --mem=$(( n * 4000 ))M"
      echo "#SBATCH --error=$G/logs/v11rec-%A.err"
      echo "#SBATCH --output=$G/logs/v11rec-%A.out"
      echo "#SBATCH --time=4:00:00"
      echo "export PATH=/sdf/home/t/tamasvami/.local/bin:\$PATH"
      echo "cd $M"
      echo "denv_workspace=\"$D\" denv fire-parallel $CFG {} ::: $(tr '\n' ' ' < $g)"
    } > $JF
    sbatch $JF >> $LOG 2>&1
    sleep 3
  done
  echo "$(date '+%F %T') round $round: resubmitted $N" >> $LOG
  sleep 180
done

drain
echo "$(date '+%F %T') all rounds done, merging" >> $LOG
bash hadd_v492.sh >> $LOG 2>&1

echo "=== identity check and PNet comparison ===" >> $LOG
denv python3 chk_pnetv11.py analysis analysis_pnetv11 >> $LOG 2>&1

echo "=== CnC and PNet flows, all samples ===" >> $LOG
denv python3 dump_cnc_pnet.py --ana $ANA ecal_pn_v15_8gev ecal_conversion_v15_8gev \
  target_pn_v15_8gev target_conversion_v15_8gev \
  signal_v15_8gev_0.001 signal_v15_8gev_0.01 signal_v15_8gev_0.1 signal_v15_8gev_1.0 \
  >> $LOG 2>&1

denv python3 make_cnc_pnet_tables.py --ana $ANA > $SO/pnetv11_tables.tex 2>>$LOG
echo "$(date '+%F %T') driver done" >> $LOG
