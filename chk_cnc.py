import ROOT, glob, os
ROOT.gROOT.SetBatch(True); ROOT.gErrorIgnoreLevel = ROOT.kError
for p in sorted(glob.glob("analysis/*_histos.root")):
    f = ROOT.TFile.Open(p); d = f.Get("CutBasedDM")
    cnc = bool(d and d.Get("CnCCutFlow_RecoilX"))
    pn = bool(d and d.Get("PNetCutFlow_RecoilX"))
    n = d.GetListOfKeys().GetEntries() if d else 0
    print("  %-48s CnC=%-5s PNet=%-5s keys=%d" % (os.path.basename(p), cnc, pn, n))
    f.Close()
