import ROOT, sys, os
ROOT.gROOT.SetBatch(True); ROOT.gErrorIgnoreLevel = ROOT.kError
# which tree to read, from "--ana DIR"; not the environment, denv does not
# copy env vars into the container and the default would silently win
ANA = 'analysis'
if '--ana' in sys.argv:
    _i = sys.argv.index('--ana')
    ANA = sys.argv[_i + 1]
    del sys.argv[_i:_i + 2]
sys.stderr.write('reading %s/\n' % ANA)
def flow(stem, hname):
    p = "%s/%s_histos.root" % (ANA, stem)
    if not os.path.exists(p): return None
    f = ROOT.TFile.Open(p); d = f.Get("CutBasedDM")
    h = d.Get(hname) if d else None
    if not h: f.Close(); return None
    px = h.ProjectionX()
    out = [(px.GetXaxis().GetBinLabel(i+1), px.GetBinContent(i+1))
           for i in range(px.GetNbinsX())]
    f.Close(); return [(l,v) for l,v in out if l.strip()]
for hname in ("CnCCutFlow_RecoilX", "PNetCutFlow_RecoilX"):
    print("############", hname)
    stems = sys.argv[1:]
    data = {s: flow(s, hname) for s in stems}
    ref = next((v for v in data.values() if v), None)
    if not ref: print("  all missing"); continue
    print("%-22s %s" % ("cut", " ".join("%16s" % s[:16] for s in stems)))
    for i,(lab,_) in enumerate(ref):
        row = []
        for s in stems:
            v = data[s]
            row.append("%16.0f" % v[i][1] if v else "%16s" % "--")
        print("%-22s %s" % (lab[:22], " ".join(row)))
