#!/usr/bin/env python3
"""List the histograms in a CutBasedDM output file."""
import sys

import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kFatal

f = ROOT.TFile.Open(sys.argv[1])
d = f.Get('CutBasedDM')
for k in d.GetListOfKeys():
    o = k.ReadObj()
    cls = o.ClassName()
    if cls.startswith('TH2'):
        shape = '%dx%d' % (o.GetNbinsX(), o.GetNbinsY())
        rng = 'y [%g, %g]' % (o.GetYaxis().GetXmin(), o.GetYaxis().GetXmax())
    else:
        shape = '%d' % o.GetNbinsX()
        rng = 'x [%g, %g]' % (o.GetXaxis().GetXmin(), o.GetXaxis().GetXmax())
    print('%-36s %-8s %-10s %-26s %s'
          % (k.GetName(), cls, shape, o.GetYaxis().GetTitle(), rng))
f.Close()
