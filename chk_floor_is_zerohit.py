import ROOT
ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kFatal
for tree, note in (('analysis_nhits', 'before the hit requirement'), ('analysis_aligned', 'with the hit requirement')):
    f = ROOT.TFile.Open('%s/ecal_pn_v15_8gev_histos.root' % tree)
    h = f.Get('CutBasedDM').Get('PNetDisc')
    b = h.GetXaxis().FindBin(1.0)
    top = h.Integral(b, h.GetNbinsX() + 1)
    print('%-18s %-28s entries %10.0f   disc >= 1.0: %7.0f   underflow (disc -99): %6.0f'
          % (tree, note, h.GetEntries(), top, h.GetBinContent(0)))
    f.Close()
