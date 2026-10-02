#!/usr/bin/env python3
"""Which reco files carry the zero-ECal-hit defect, and what is in them.

Only reads the files inside chunks known (from analysis_pnetv11) to hold any
zero-hit event, so it is fast. Per file: events, zero-hit events, how many have
run number -1, and the distinct runs involved.
"""
import glob
import os

import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kFatal

RECO = '/sdf/data/ldmx/private_production/mc26/reco_v492/ecal_pn_v15_8gev'
ANA = 'analysis_pnetv11/ecal_pn_v15_8gev'
PER_TASK = 5
STAGE = 3

files = sorted(glob.glob(RECO + '/*_reco.root'))
chunks = [files[i:i + PER_TASK] for i in range(0, len(files), PER_TASK)]

cand = []
for c in chunks:
    h = '%s/%s_histo.root' % (ANA, os.path.basename(c[-1])[:-5])
    f = ROOT.TFile.Open(h)
    if not f or f.IsZombie():
        continue
    py = f.Get('CutBasedDM').Get('NReadoutHits').ProjectionY('p', STAGE + 1, STAGE + 1)
    if py.GetBinContent(1) > 0:
        cand.extend(c)
    f.Close()

print('candidate files (in chunks with any zero-hit event): %d' % len(cand))
rows = []
for p in cand:
    f = ROOT.TFile.Open(p)
    t = f.Get('LDMX_Events')
    n_all = t.GetEntries()
    n_zero = t.Draw('EventHeader.run_', 'EcalVeto_reco.n_readout_hits_ == 0', 'goff')
    zruns = set(int(t.GetV1()[i]) for i in range(n_zero))
    n_neg = t.GetEntries('EventHeader.run_ < 0')
    n_negzero = t.GetEntries('EventHeader.run_ < 0 && EcalVeto_reco.n_readout_hits_ == 0')
    m = t.Draw('EventHeader.run_', '', 'goff')
    allruns = set(int(t.GetV1()[i]) for i in range(m))
    f.Close()
    if n_zero or n_neg:
        rows.append((os.path.basename(p), n_all, n_zero, n_neg, n_negzero,
                     len(allruns), len(zruns)))

rows.sort(key=lambda r: -r[2])
print('files with zero-hit or run<0 events: %d' % len(rows))
print('%-58s %7s %7s %7s %9s %6s %6s'
      % ('file', 'events', 'zero', 'run<0', 'run<0&0', 'runs', 'zruns'))
for r in rows:
    print('%-58s %7d %7d %7d %9d %6d %6d' % r)

big = [r for r in rows if r[2] >= 50]
print()
print('files with >= 50 zero-hit events: %d, holding %d zero-hit of %d total, '
      'and %d events overall'
      % (len(big), sum(r[2] for r in big), sum(r[2] for r in rows),
         sum(r[1] for r in big)))
