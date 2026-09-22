import ROOT, os, sys
ROOT.gROOT.SetBatch(True); ROOT.gErrorIgnoreLevel = ROOT.kError
d = sys.argv[1]
tot = 0
files = sorted(os.listdir(d))
for fn in files:
    if not fn.endswith('_histo.root'): continue
    p = os.path.join(d, fn)
    f = ROOT.TFile.Open(p)
    v = -1
    if f and not f.IsZombie():
        dd = f.Get('CutBasedDM')
        h = dd.Get('StdCutFlowWithTracking_RecoilX') if dd else None
        if h: v = h.ProjectionX().GetBinContent(1)
        f.Close()
    tot += max(v, 0)
    print("  %9.0f  %s" % (v, fn[:70]))
print("TOTAL All = %.0f over %d histo files" % (tot, sum(1 for x in files if x.endswith('_histo.root'))))
