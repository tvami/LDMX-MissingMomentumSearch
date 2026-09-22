import ROOT, sys, os
ROOT.gROOT.SetBatch(True); ROOT.gErrorIgnoreLevel = ROOT.kError
LAB = ["All","Min energy","Min tk hits","Ecal hit","Hcal hit","Acceptance"]
print("%-26s %s" % ("sample", " ".join("%12s" % l for l in LAB)))
for stem in sys.argv[1:]:
    p = "analysis/%s_histos.root" % stem
    if not os.path.exists(p): print("%-26s MISSING" % stem); continue
    f = ROOT.TFile.Open(p); d = f.Get("CutBasedDM")
    h = d.Get("Acceptance") if d else None
    if not h: print("%-26s no Acceptance hist" % stem); continue
    px = h.ProjectionX()
    v = [px.GetBinContent(i+1) for i in range(6)]
    print("%-26s %s" % (stem, " ".join("%12.0f" % x for x in v)))
    f.Close()
