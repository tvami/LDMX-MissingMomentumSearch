#!/usr/bin/env python3
"""Unit test check on one v11 ParticleNet histogram file.

Confirms the disc really does saturate at 1, which is why the analyzer has to
take passesVeto() from the processor instead of cutting on the disc itself.
"""
import sys

import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kFatal

f = ROOT.TFile.Open(sys.argv[1])
d = f.Get('CutBasedDM')

px = d.Get('PNetCutFlow_RecoilX').ProjectionX()
labels = ['acceptance', 'trigger', 'loosePresel', 'pnet', 'hcalMaxPE<8']
print('PNet flow:')
for i, lab in enumerate(labels):
    print('  %-13s %8.0f' % (lab, px.GetBinContent(i + 1)))

h = d.Get('PNetDisc')
print('\nPNetDisc: %d entries, mean %.4f' % (h.GetEntries(), h.GetMean()))
n = h.GetNbinsX()
top = h.GetBinContent(n)          # the 1.0 bin
print('  in the top bin (disc = 1 within float): %.0f (%.1f%%)'
      % (top, 100 * top / h.GetEntries() if h.GetEntries() else 0))
print('  underflow (disc = -99, PNet not run): %.0f' % h.GetBinContent(0))
print('  bins with any entries:')
for i in range(1, n + 1):
    c = h.GetBinContent(i)
    if c:
        print('    [%.3f, %.3f) %8.0f' %
              (h.GetXaxis().GetBinLowEdge(i), h.GetXaxis().GetBinUpEdge(i), c))

print('\nStdCutFlowWithTracking (for the identity check later):')
sx = d.Get('StdCutFlowWithTracking_RecoilX').ProjectionX()
print('  ' + ' '.join('%.0f' % sx.GetBinContent(i + 1) for i in range(8)))
f.Close()
