#!/bin/bash
# Drive the analysis_aligned run (all eight samples) to completion:
# wait, recover missing chunks, hadd, then build the aligned tables and the PNet threshold scan.
#
# The drain ignores jobs named cnc_*, so the cut-and-count ntuple campaign
# (PLAN_CNC_PUNZI.md) can run alongside without holding this up.
export PATH=/sdf/home/t/tamasvami/.local/bin:$PATH
D=/sdf/group/ldmx/users/tamasvami/ldmx-analysis/v4.9.2/ldmx-sw
M=$D/LDMX-MissingMomentumSearch
SO=$D/scan_out
LOG=$SO/drive_aligned.log
G=/sdf/group/ldmx/users/tamasvami/slurm
CFG=cfg_ana_cutBasedDM_aligned.py
MAXROUND=${MAXROUND:-4}
# --ana on the command line: denv drops exported env vars
ANA=analysis_aligned
# hadd_v492.sh is host bash, so this does reach it
export ANA_DIR=$ANA
cd $M || exit 1

# sample:files_per_task, must match toSumbitMCProd_ana_aligned.sh
SF="ecal_pn_v15_8gev:5 ecal_conversion_v15_8gev:1 target_pn_v15_8gev:5
    target_conversion_v15_8gev:4 signal_v15_8gev/1.0:1 signal_v15_8gev/0.1:1
    signal_v15_8gev/0.01:1 signal_v15_8gev/0.001:1"

drain () {
  while true; do
    Q=$(squeue -u tamasvami -h -t R,PD -o '%j %r' 2>/dev/null \
        | awk '$2 != "JobHeldUser" && $1 !~ /^cnc_/' | grep -c .)
    [ "$Q" -eq 0 ] && break
    sleep 120
  done
}

echo "$(date '+%F %T') driver start" > $LOG

for round in $(seq 1 $MAXROUND); do
  echo "$(date '+%F %T') round $round: waiting for drain" >> $LOG
  drain
  echo "$(date '+%F %T') round $round: drained, checking" >> $LOG

  : > /tmp/aln_missing.txt
  for sf in $SF ; do
    s=${sf%:*}; f=${sf#*:}
    tag=$(echo $s | tr '/' '_')
    denv python3 prune_strays.py --ana $ANA $s $f --apply >> $LOG 2>&1
    denv python3 find_missing_chunks.py --ana $ANA $s $f $G/filelists/alnrec_$tag \
      >> /tmp/aln_missing.txt 2>>$LOG
  done
  N=$(grep -c . /tmp/aln_missing.txt)
  echo "$(date '+%F %T') round $round: $N chunks missing" >> $LOG
  [ "$N" -eq 0 ] && break

  rm -f /tmp/alng_*
  split -l 16 -d -a 4 /tmp/aln_missing.txt /tmp/alng_
  for g in /tmp/alng_* ; do
    n=$(grep -c . $g)
    JF=$G/jobs/alnrec_r${round}_$(basename $g).job
    {
      echo '#!/bin/bash'
      echo "#SBATCH --partition=roma"
      echo "#SBATCH --account=ldmx"
      echo "#SBATCH --nodes=1"
      echo "#SBATCH --ntasks=$n"
      echo "#SBATCH --cpus-per-task=1"
      echo "#SBATCH --mem=$(( n * 4000 ))M"
      echo "#SBATCH --error=$G/logs/alnrec-%A.err"
      echo "#SBATCH --output=$G/logs/alnrec-%A.out"
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

echo "=== aligned tables and PNet threshold scan ===" >> $LOG
denv python3 make_tables_aligned.py --ana $ANA > ../scan_out/tables_aligned.tex 2>> $LOG; cat ../scan_out/tables_aligned.tex >> $LOG
echo "$(date '+%F %T') driver done" >> $LOG
