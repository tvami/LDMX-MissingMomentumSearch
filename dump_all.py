import ROOT, sys, os
ROOT.gROOT.SetBatch(True); ROOT.gErrorIgnoreLevel = ROOT.kError
LAB = ["All","Fiducial","Trig","Presel","TrkVeto","EcalVeto","MIP","HCal"]
print("%-34s %10s %10s %10s %10s %10s %10s %10s %10s" % tuple(["sample"]+LAB))
for stem in sys.argv[1:]:
    p = "analysis/%s_histos.root" % stem
    if not os.path.exists(p):
        print("%-34s MISSING" % stem); continue
    f = ROOT.TFile.Open(p); d = f.Get("CutBasedDM")
    h = d.Get("StdCutFlowWithTracking_RecoilX") if d else None
    if not h:
        print("%-34s no hist" % stem); continue
    px = h.ProjectionX()
    v = [px.GetBinContent(i+1) for i in range(8)]
    print("%-34s %s" % (stem, " ".join("%10.0f" % x for x in v)))
    f.Close()
