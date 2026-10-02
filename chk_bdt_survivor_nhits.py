import ROOT
ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kFatal
f = ROOT.TFile.Open('analysis_nhits/ecal_pn_v15_8gev_histos.root')
d = f.Get('CutBasedDM')
h = d.Get('NReadoutHits')
labels = ['All', 'Fiducial', 'Trig', 'Presel', 'Tracker veto', 'ECal veto (BDT)', 'MIP veto', 'HCal veto']
for st in range(8):
    py = h.ProjectionY('p%d' % st, st + 1, st + 1)
    print('%-16s total %10.0f   N_hits=0 %7.0f' % (labels[st], py.Integral(0, py.GetNbinsX() + 1), py.GetBinContent(1)))
