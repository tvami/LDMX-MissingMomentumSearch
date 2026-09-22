#!/usr/bin/env python
"""Strip Jihoon's signal files and re-reco them in v4.8.3, on POD.

Two stages in one job per chunk:
  1. strip_signal.py  - drop the stale reco_v1 pass and the unused sim
     collections, outside ldmx-sw (see strip_signal.py for why)
  2. cfg_reco_signal_v483.py - the full v4.8.3 reco from the sim hits

One fire per input file, GNU parallel inside a single SLURM job, so a crashing
file costs one file. POD wants few jobs, so everything goes in two.

  python3 submit_strip_and_reco.py [--bdt segmip] [-j 10] [--test]
"""
import argparse
import glob
import os
import subprocess
from datetime import datetime

LDMX_SW = "/home/vamitamas/ldmx-analysis/v4.8.3/ldmx-sw"
SRC = "/home/jihoonyoo/LDMX/8GeV_Samples/v15_plot400/sig_reco"
STRIPPED = "/home/vamitamas/Samples8GeV/sig_stripped"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bdt", default="segmip")
    ap.add_argument("-j", "--jobs", type=int, default=10)
    ap.add_argument("-n", "--nchunks", type=int, default=2)
    ap.add_argument("-m", "--mem", default="64000M")
    ap.add_argument("--test", action="store_true")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(SRC, "*_reco_v1.root")))
    if not files:
        raise SystemExit("no input files found in %s" % SRC)
    print("%d input files" % len(files))

    os.makedirs(STRIPPED, exist_ok=True)
    jobdir = "/home/vamitamas/slurm/jobs/"
    logdir = "/home/vamitamas/slurm/logs/"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # a tiny per-file driver: strip then reco, skipping the strip if it is
    # already there so the job can be re-run cheaply
    driver = os.path.join(LDMX_SW, "strip_and_reco_one.sh")
    with open(driver, "w") as f:
        f.write("#!/bin/bash\n")
        f.write("set -o pipefail\n")
        f.write('src="$1"\n')
        f.write('base=$(basename "$src")\n')
        f.write('stripped="%s/$base"\n' % STRIPPED)
        f.write('cd %s\n' % LDMX_SW)
        f.write('if [ ! -s "$stripped" ]; then\n')
        f.write('  denv python3 strip_signal.py "$src" "$stripped" || exit 0\n')
        f.write("fi\n")
        f.write('LDMX_BDT=%s denv fire cfg_reco_signal_v483.py "$stripped"\n' % args.bdt)
        f.write("exit 0\n")  # a crash must not fail the whole job
    os.chmod(driver, 0o755)

    chunk = (len(files) + args.nchunks - 1) // args.nchunks
    for ic in range(args.nchunks):
        part = files[ic * chunk:(ic + 1) * chunk]
        if not part:
            continue
        # GNU parallel is only inside the container; xargs is always here
        listfile = "%s/sigreco483_%s_%d_%s.list" % (jobdir, args.bdt, ic, stamp)
        with open(listfile, "w") as lf:
            lf.write("\n".join(part) + "\n")
        cmd = "xargs -P %d -n 1 %s < %s" % (args.jobs, driver, listfile)
        job_file = "%s/sigreco483_%s_%d_%s.job" % (jobdir, args.bdt, ic, stamp)
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
            f.write("#SBATCH --mail-type=FAIL\n\n")
            f.write('export PATH="$HOME/.local/bin:$PATH"\n\n')
            f.write("cd $SLURM_SUBMIT_DIR\n\n/bin/hostname\n\n")
            f.write("%s\nexit 0\n" % cmd)
        print("chunk %d: %d files -> %s" % (ic, len(part), job_file))
        if not args.test:
            subprocess.Popen("sbatch -p batch %s" % job_file, shell=True).wait()


if __name__ == "__main__":
    main()
