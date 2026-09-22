#!/usr/bin/env python
"""Re-run the input files of the reco tasks that crashed, ONE fire per file.

The first pass packed 20 input files into a single fire invocation, so a single
bad event took the whole task down and cost all 20 files. The crash is
deterministic and BDT-independent (segmip and helena died at identical event
counts on the same tasks), so re-running the same inputs at 1:1 granularity
isolates the damage to the individual files that contain the bad events.

Usage:
  cd /home/vamitamas/ldmx-analysis/v4.8.2/ldmx-sw
  python3 submit_pod_reco_recover.py -py cfg_reco_dropsim_segmip.py \
      -T v482segmip -s ecal_pn_v15_8gev_batch2 -l <failed filelist> [-l ...]
"""
import argparse
import logging
import os
import subprocess
from datetime import datetime

LDMX_SW = "/home/vamitamas/ldmx-analysis/v4.8.2/ldmx-sw"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-py", "--script", required=True)
    ap.add_argument("-T", "--tag", required=True)
    ap.add_argument("-s", "--sample", required=True)
    ap.add_argument("-l", "--filelist", action="append", required=True,
                    help="a failed task filelist; repeatable")
    ap.add_argument("-j", "--jobs", type=int, default=16,
                    help="GNU parallel concurrency (default 16)")
    ap.add_argument("-m", "--mem", default="64000M")
    ap.add_argument("-t", "--test", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(format="[ recover ][ %(levelname)s ]: %(message)s",
                        level=logging.DEBUG)

    files = []
    for fl in args.filelist:
        files.extend(open(fl).read().split())
    files = sorted(set(files))
    logging.info("%d input files to re-run at 1:1 granularity", len(files))

    jobdir = "/home/vamitamas/slurm/jobs/"
    logdir = "/home/vamitamas/slurm/logs/"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # fire-parallel runs one `fire <cfg> <file>` per ::: value
    command = (
        'denv_workspace="%s" denv fire-parallel %s -- -j %d ::: %s'
        % (LDMX_SW, args.script, args.jobs, " ".join(files))
    )

    job_file = "%s/recover_%s_%s_%s.job" % (jobdir, args.tag, args.sample, stamp)
    with open(job_file, "w") as f:
        f.write("#!/bin/bash\n\n")
        f.write("#SBATCH --partition=batch\n")
        f.write("#SBATCH --nodes=1\n")
        f.write("#SBATCH --ntasks-per-node=%d\n" % args.jobs)
        f.write("#SBATCH --ntasks=%d\n" % args.jobs)
        f.write("#SBATCH --cpus-per-task=1\n")
        f.write("#SBATCH --mem=%s\n" % args.mem)
        f.write("#SBATCH --error=%s/slurm-%%A_%%a.err\n" % logdir)
        f.write("#SBATCH --output=%s/slurm-%%A_%%a.out\n" % logdir)
        f.write("#SBATCH --time=120:05:00\n")
        f.write("#SBATCH --mail-type=FAIL\n")
        f.write("#SBATCH --mail-user=tamasvami@ucsb.edu\n\n")
        f.write('export PATH="$HOME/.local/bin:$PATH"\n\n')
        f.write("cd $SLURM_SUBMIT_DIR\n\n")
        f.write("/bin/hostname\n\n")
        # a crashing fire must not abort the whole job
        f.write("%s\nexit 0\n" % command)

    logging.info("job file: %s", job_file)
    if args.test:
        logging.info("test mode, not submitting")
        print(command[:400] + " ...")
        return
    subprocess.Popen("sbatch -p batch %s" % job_file, shell=True).wait()


if __name__ == "__main__":
    main()
