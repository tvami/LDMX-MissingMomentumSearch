#!/usr/bin/env python3
"""Unit test check on one analysis_notrk file (reference ECal PN file).

  - every existing flow reproduces the earlier unit tests exactly
  - PNetNoTrk up to the ParticleNet row equals the old PNet flow (49 there),
    since the only extra cut, N_straight, comes after it
  - BDTNoTrk at the BDT row is >= the BDT row of the tracked flow (36), since it
    drops a cut
  - all new flows are non-increasing
"""
import sys

import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kFatal

f = ROOT.TFile.Open(sys.argv[1])
d = f.Get('CutBasedDM')


def bins(name):
    px = d.Get(name).ProjectionX()
    return [px.GetBinContent(i + 1) for i in range(px.GetNbinsX())], \
        [px.GetXaxis().GetBinLabel(i + 1) for i in range(px.GetNbinsX())]


ok = True
EXPECT = {'PNetCutFlow_RecoilX': [9315, 9315, 2289, 49, 0],
          'CnCCutFlow_RecoilX': [9315, 9315, 8281, 693, 542, 430, 429, 359, 301, 278, 0],
          'StdCutFlowWithTracking_RecoilX': [9315, 9315, 9315, 9315, 8392, 36, 36, 0],
          'PNetAlignedCutFlow_RecoilX': [9315, 9315, 9315, 2289, 2087, 44, 43, 0]}
for name, exp in EXPECT.items():
    got = [int(x) for x in bins(name)[0][:len(exp)]]
    same = got == exp
    ok &= same
    print('%-32s %s %s' % (name, 'OK  ' if same else 'DIFF', got))

pnt, plab = bins('PNetNoTrkCutFlow_RecoilX')
bnt, blab = bins('BDTNoTrkCutFlow_RecoilX')
for name, v, lab in (('PNetNoTrkCutFlow_RecoilX', pnt, plab), ('BDTNoTrkCutFlow_RecoilX', bnt, blab)):
    mono = all(v[i + 1] <= v[i] for i in range(len(v) - 1))
    ok &= mono
    print('%-32s %s' % (name, 'monotonic' if mono else 'NOT MONOTONIC'))
    for x, l in zip(v, lab):
        print('    %-30s %8.0f' % (l, x))

c1 = pnt[4] == 49
c2 = bnt[3] >= 36
ok &= c1 and c2
print('PNetNoTrk ParticleNet row == 49 (old flow):', 'OK' if c1 else 'DIFF %.0f' % pnt[4])
print('BDTNoTrk BDT row >= 36 (tracked flow):', 'OK' if c2 else 'DIFF %.0f' % bnt[3])
print('PNetNoTrkDiscPostAll entries %.0f' % d.Get('PNetNoTrkDiscPostAll').GetEntries())
print('ALL CHECKS PASS' if ok else 'SOMETHING DIFFERS')
f.Close()
