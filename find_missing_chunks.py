#!/usr/bin/env python3
"""Which 20-file analysis chunks never produced a histogram.

submit_sdf_mt_input.py chunks sorted(glob(indir/pattern)) into groups of
FILES_PER_TASK, and cfg_ana_cutBasedDM_v492.py names the output after the LAST
file of the chunk. That is deterministic, so the missing chunks can be
recovered exactly rather than rerunning the whole sample.

Writes one filelist per missing chunk and prints their paths.
"""
import glob
import os
import sys

import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kFatal


def usable(path):
    """A histogram file counts only if it actually holds histograms.

    A job that is killed or hangs leaves a ~500 byte file that exists and is
    non-empty on disk but has no keys, because the histograms are only written
    at close. Checking size alone silently accepts those.
    """
    if not os.path.exists(path) or os.path.getsize(path) < 1000:
        return False
    f = ROOT.TFile.Open(path)
    if not f or f.IsZombie():
        return False
    d = f.Get('CutBasedDM')
    ok = bool(d) and d.GetListOfKeys().GetEntries() > 0
    f.Close()
    return ok

RECO = '/sdf/data/ldmx/private_production/mc26/reco_v492/'
ANA = 'analysis/'
# must match the -f given to submit_sdf_mt_input.py: 20 for the backgrounds,
# 10 for signal. Getting this wrong mis-identifies which chunks are missing.
FILES_PER_TASK = 20


def main():
    sample = sys.argv[1]
    per_task = int(sys.argv[2]) if len(sys.argv) > 2 else FILES_PER_TASK
    outdir = sys.argv[3] if len(sys.argv) > 3 else '/sdf/home/t/tamasvami/slurm/filelists/ana492_recover'
    os.makedirs(outdir, exist_ok=True)
    for f in glob.glob(outdir + '/*.txt'):
        os.remove(f)

    files = sorted(glob.glob(RECO + sample + '/*_reco.root'))
    chunks = [files[i:i + per_task] for i in range(0, len(files), per_task)]

    missing, present = [], 0
    for c in chunks:
        histo = os.path.join(ANA, sample,
                             os.path.basename(c[-1])[:-5] + '_histo.root')
        if usable(histo):
            present += 1
        else:
            missing.append(c)

    for i, c in enumerate(missing):
        p = '%s/recover_%s_%04d.txt' % (outdir, sample.replace('/', '_'), i)
        with open(p, 'w') as fh:
            fh.write(' '.join(c))
        print(p)

    sys.stderr.write('%s: %d chunks, %d present, %d missing (%d files)\n'
                     % (sample, len(chunks), present, len(missing),
                        sum(len(c) for c in missing)))


if __name__ == '__main__':
    main()
