#!/usr/bin/env python3
"""Provisional survivor composition from whatever ECal PN chunks have finished.

Sums the N_hits distribution at the last stage of both flows over every
completed file in analysis_nhits/ecal_pn_v15_8gev, skipping files still being
written (they have no keys until close). Gives the fraction of survivors with
zero ECal hits before the full campaign and its merge are done.
"""
import glob
import os
import sys

import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kFatal

ANA = sys.argv[1] if len(sys.argv) > 1 else 'analysis_nhits'
FLOWS = [('CnCCutFlow_NHits', 10, 'cut and count'),
         ('PNetCutFlow_NHits', 4, 'ParticleNet')]

files = sorted(glob.glob('%s/ecal_pn_v15_8gev/*_histo.root' % ANA))
tot = {h: 0.0 for h, _, _ in FLOWS}
zero = {h: 0.0 for h, _, _ in FLOWS}
used = 0
for p in files:
    if os.path.getsize(p) < 1000:
        continue
    f = ROOT.TFile.Open(p)
    if not f or f.IsZombie():
        continue
    d = f.Get('CutBasedDM')
    if not d or d.GetListOfKeys().GetEntries() == 0:
        f.Close()
        continue
    for h, stage, _ in FLOWS:
        h2 = d.Get(h)
        py = h2.ProjectionY('py_%d_%s' % (used, h), stage + 1, stage + 1)
        tot[h] += py.Integral(0, py.GetNbinsX() + 1)
        zero[h] += py.GetBinContent(1)
    f.Close()
    used += 1

print('completed ECal PN chunks used: %d of 1185 (%.0f%% of the sample)'
      % (used, 100.0 * used / 1185))
for h, _, lab in FLOWS:
    print('%-14s survivors: %4.0f raw, of which N_hits = 0: %4.0f (%.0f%%)'
          % (lab, tot[h], zero[h], 100 * zero[h] / tot[h] if tot[h] else 0))
