#!/usr/bin/env python3
"""Unit test check on one analysis_nhits file.

The PNet flow must match the earlier v11 unit test on the same file
(9315 9315 2289 49 0), and the four new histograms must be filled.
"""
import sys

import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kFatal

f = ROOT.TFile.Open(sys.argv[1])
d = f.Get('CutBasedDM')

px = d.Get('PNetCutFlow_RecoilX').ProjectionX()
print('PNet flow:', ' '.join('%.0f' % px.GetBinContent(i + 1) for i in range(5)),
      '  (expect 9315 9315 2289 49 0)')

for name in ('PNetDiscPostHcal', 'PNetDiscPostHcalWithHit'):
    h = d.Get(name)
    print('%-26s entries %6.0f, above 0.5664: %4.0f'
          % (name, h.GetEntries(),
             h.Integral(h.GetXaxis().FindBin(0.5664 + 1e-9), h.GetNbinsX() + 1)))

for name, n in (('PNetCutFlow_NHits', 5), ('CnCCutFlow_NHits', 11)):
    h = d.Get(name)
    row = []
    for i in range(n):
        py = h.ProjectionY('%s_%d' % (name, i), i + 1, i + 1)
        row.append('%.0f(%.0f)' % (py.Integral(0, py.GetNbinsX() + 1),
                                   py.GetBinContent(1)))
    print('%-18s per stage, total(N_hits=0): %s' % (name, ' '.join(row)))
f.Close()
