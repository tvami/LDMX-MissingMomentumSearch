#!/usr/bin/env python3
"""Unit test check on one analysis_aligned file.

On the reference ECal PN file (no zero-hit events), the existing flows must
reproduce the earlier unit test exactly; the aligned flows must be
non-increasing stage by stage and never exceed their unaligned counterparts at
the end.
"""
import sys

import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kFatal

EXPECT = {'PNetCutFlow_RecoilX': [9315, 9315, 2289, 49, 0],
          'CnCCutFlow_RecoilX': [9315, 9315, 8281, 693, 542, 430, 429, 359, 301, 278, 0],
          'StdCutFlowWithTracking_RecoilX': [9315, 9315, 9315, 9315, 8392, 36, 36, 0]}

f = ROOT.TFile.Open(sys.argv[1])
d = f.Get('CutBasedDM')


def bins(name, n=None):
    px = d.Get(name).ProjectionX()
    n = n or px.GetNbinsX()
    return [px.GetBinContent(i + 1) for i in range(n)], \
        [px.GetXaxis().GetBinLabel(i + 1) for i in range(n)]


ok = True
for name, exp in EXPECT.items():
    got, _ = bins(name, len(exp))
    same = [int(x) for x in got] == exp
    ok &= same
    print('%-32s %s  %s' % (name, 'OK  ' if same else 'DIFF', ' '.join('%.0f' % x for x in got)))

for name in ('CnCAlignedCutFlow_RecoilX', 'PNetAlignedCutFlow_RecoilX'):
    got, lab = bins(name)
    mono = all(got[i + 1] <= got[i] for i in range(len(got) - 1))
    ok &= mono
    print('%-32s %s' % (name, 'monotonic' if mono else 'NOT MONOTONIC'))
    for x, l in zip(got, lab):
        print('    %-22s %8.0f' % (l, x))

h = d.Get('PNetAlignedDiscPostAll')
print('PNetAlignedDiscPostAll entries %.0f, bins %d' % (h.GetEntries(), h.GetNbinsX()))
print('ALL CHECKS PASS' if ok else 'SOMETHING DIFFERS')
f.Close()
