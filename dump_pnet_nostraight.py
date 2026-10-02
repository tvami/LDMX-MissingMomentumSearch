import glob
import ROOT
ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kFatal
PRES = '/sdf/data/ldmx/private_production/mc26/pres_skim/'
RECO = '/sdf/data/ldmx/private_production/mc26/reco_v492/'
BKGS = [('ecal_pn_v15_8gev', 1.5e14), ('ecal_conversion_v15_8gev', 1.0e15),
        ('target_pn_v15_8gev', 1.0e15), ('target_conversion_v15_8gev', 1.0e15)]
def cov(s):
    ni = len(glob.glob(PRES + s + '/*.root')); no = len(glob.glob(RECO + s + '/*_reco.root'))
    return float(ni) / no
tot = 0
for s, e in BKGS:
    f = ROOT.TFile.Open('analysis_aligned/%s_histos.root' % s)
    n = f.Get('CutBasedDM').Get('PNetCutFlow_RecoilX').ProjectionX().GetBinContent(5)
    w = 1.5e14 / e * cov(s); tot += n * w
    print('%-28s raw %3.0f -> %.2f' % (s, n, n * w)); f.Close()
print('all bkg %.2f' % tot)
for m, t in (('0.001', 0.8641), ('0.01', 0.8578), ('0.1', 0.8672), ('1.0', 0.8648)):
    f = ROOT.TFile.Open('analysis_aligned/signal_v15_8gev_%s_histos.root' % m)
    px = f.Get('CutBasedDM').Get('PNetCutFlow_RecoilX').ProjectionX()
    print('signal %-6s %.1f%%' % (m, 100 * t * px.GetBinContent(5) / px.GetBinContent(1))); f.Close()
