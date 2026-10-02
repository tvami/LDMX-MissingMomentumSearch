#!/usr/bin/env python3
"""Pin the zero-ECal-hit events to the simulation runs that produced them.

Each reco file merges ~40 simulation runs, so the run number in a file name only
names the last of them. The event header carries the true run, so count
zero-hit events per run directly from the reco trees.

Reads every ECal PN reco file once: per file, the number of events and the run
numbers of the events with no ECal readout hits.
"""
import collections
import glob
import os
import sys

import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kFatal
for lib in ('libFramework.so', 'libEcal_Event.so'):
    ROOT.gSystem.Load(lib)

RECO = '/sdf/data/ldmx/private_production/mc26/reco_v492/ecal_pn_v15_8gev'
files = sorted(glob.glob(RECO + '/*_reco.root'))
if len(sys.argv) > 1:
    files = files[:int(sys.argv[1])]

per_run_zero = collections.Counter()
per_run_all = collections.Counter()
bad_files = []
for k, p in enumerate(files):
    f = ROOT.TFile.Open(p)
    t = f.Get('LDMX_Events') if f else None
    if not t:
        continue
    n = t.Draw('EventHeader.run_', 'EcalVeto_reco.n_readout_hits_ == 0', 'goff')
    if n < 0:
        sys.exit('branch names wrong: Draw returned %d on %s' % (n, p))
    zruns = [int(t.GetV1()[i]) for i in range(n)]
    for r in zruns:
        per_run_zero[r] += 1
    if n:
        bad_files.append((os.path.basename(p), n, t.GetEntries()))
        # all-event run counts only for files that matter, to keep this fast
        m = t.Draw('EventHeader.run_', '', 'goff')
        for i in range(m):
            per_run_all[int(t.GetV1()[i])] += 1
    f.Close()
    if k % 500 == 0:
        sys.stderr.write('%d/%d files\n' % (k, len(files)))

tz = sum(per_run_zero.values())
print('files read: %d   zero-hit events: %d   in %d files   from %d sim runs'
      % (len(files), tz, len(bad_files), len(per_run_zero)))

print()
print('sim runs with zero-hit events, worst first:')
print('  %10s %8s %8s %8s' % ('run', 'zero', 'events', 'frac'))
for r, z in per_run_zero.most_common(25):
    a = per_run_all.get(r, 0)
    print('  %10d %8d %8d %7.1f%%' % (r, z, a, 100.0 * z / a if a else 0))

runs = sorted(per_run_zero)
if not runs:
    sys.exit('no zero-hit events in these files')
print()
print('run range of zero-hit events: %d to %d' % (runs[0], runs[-1]))
hist = collections.Counter((r // 10000) * 10000 for r in runs)
print('runs with zero-hit events, per 10k block:')
for b in sorted(hist):
    print('  %8d-%8d: %4d runs, %6d events'
          % (b, b + 9999, hist[b],
             sum(per_run_zero[r] for r in runs if (r // 10000) * 10000 == b)))
