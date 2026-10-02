#!/usr/bin/env python3
"""LaTeX for the cut-and-count and ParticleNet tables, at a common 1.5e14 EoT.

Signal efficiency follows the same convention as the BDT table: denominator is
the in-acceptance sample, so the trigger row carries the measured trigger
efficiency and later rows are cumulative through it.
"""
import os, sys
import ROOT
ROOT.gROOT.SetBatch(True); ROOT.gErrorIgnoreLevel = ROOT.kError

TGT = 1.5e14
# which tree to read, from "--ana DIR"; not the environment, denv does not
# copy env vars into the container and the default would silently win
ANA = 'analysis'
if '--ana' in sys.argv:
    _i = sys.argv.index('--ana')
    ANA = sys.argv[_i + 1]
    del sys.argv[_i:_i + 2]
sys.stderr.write('reading %s/\n' % ANA)
# sample -> (EoT, pres inputs, reco files)  for scale = TGT/EoT * coverage
BKG = {'ecal_pn_v15_8gev': (1.5e14, 6172, 5921),
       'ecal_conversion_v15_8gev': (1.0e15, 991, 933),
       'target_pn_v15_8gev': (1.0e15, 46, 46),
       'target_conversion_v15_8gev': (1.0e15, 167, 167)}
TRIG = {'signal_v15_8gev_0.001': 0.8641, 'signal_v15_8gev_0.01': 0.8578,
        'signal_v15_8gev_0.1': 0.8672, 'signal_v15_8gev_1.0': 0.8648}
SIGS = ['signal_v15_8gev_0.001', 'signal_v15_8gev_0.01',
        'signal_v15_8gev_0.1', 'signal_v15_8gev_1.0']

def flow(stem, h):
    f = ROOT.TFile.Open('%s/%s_histos.root' % (ANA, stem))
    d = f.Get('CutBasedDM'); px = d.Get(h).ProjectionX()
    out = [(px.GetXaxis().GetBinLabel(i+1), px.GetBinContent(i+1))
           for i in range(px.GetNbinsX())]
    f.Close()
    return [(l, v) for l, v in out if l.strip()]

def bkgcell(v, stem):
    eot, ni, no = BKG[stem]
    s = TGT / eot * (float(ni) / no)
    x = v * s
    return r'$<$1' if x < 1 else '{:,.0f}'.format(x)

# The PNet bin label is baked into the histograms at fill time, and the v11 run
# still carries the v10 wording. v11 does not cut on the probability at all: it
# cuts on the logit difference, from disc_cut 0.5664. Relabel here rather than
# re-running 2290 tasks for a string.
# only for the v11 tree; the v10 run really did cut the probability at 0.74
RELABEL = ({'ParticleNet > 0.74': 'ParticleNet v11 (disc 0.5664)'}
           if 'pnetv11' in ANA else {})

def table(hname, bkgs, rows_from=0):
    ref = flow(bkgs[0], hname)
    sig = {s: flow(s, hname) for s in SIGS}
    for i, (lab, _) in enumerate(ref):
        if i < rows_from:
            continue
        lab = RELABEL.get(lab, lab)
        cells = [bkgcell(flow(b, hname)[i][1], b) for b in bkgs]
        for s in SIGS:
            v = sig[s]
            eff = TRIG[s] * v[i][1] / v[0][1] if v[0][1] else 0
            cells.append('{:.1f}\\%'.format(100 * eff))
        print('%-26s & %s \\\\ \\hline' % (lab, ' & '.join(cells)))

print('%%%%%% cut and count (ECal PN, ECal conversion)')
table('CnCCutFlow_RecoilX', ['ecal_pn_v15_8gev', 'ecal_conversion_v15_8gev'])
print()
# all four backgrounds now have PNet numbers; the two conversion samples were
# previously run with the no-PNet config, so their PNet bins were exactly 0
print('%%%%%% ParticleNet (ECal PN, ECal conv., Target PN, Target conv.)')
table('PNetCutFlow_RecoilX', ['ecal_pn_v15_8gev', 'ecal_conversion_v15_8gev',
                              'target_pn_v15_8gev', 'target_conversion_v15_8gev'])
