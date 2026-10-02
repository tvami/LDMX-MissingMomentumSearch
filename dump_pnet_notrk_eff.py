import ROOT
ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kFatal
TRIG = {'0.001': 0.8641, '0.01': 0.8578, '0.1': 0.8672, '1.0': 0.8648}
for m, t in TRIG.items():
    f = ROOT.TFile.Open('analysis_notrk/signal_v15_8gev_%s_histos.root' % m)
    px = f.Get('CutBasedDM').Get('PNetNoTrkCutFlow_RecoilX').ProjectionX()
    acc, trig, fin = px.GetBinContent(1), px.GetBinContent(2), px.GetBinContent(7)
    print('%-6s acc %8.0f trig %8.0f final %8.0f   rel. triggered %.2f%%   incl. trigger %.2f%%'
          % (m, acc, trig, fin, 100 * fin / trig, 100 * t * fin / acc))
    f.Close()
