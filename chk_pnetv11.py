#!/usr/bin/env python3
"""Compare the v10 and v11 ParticleNet runs.

The two runs used the same reco, the same Humberto BDT and the same analyzer
logic everywhere except the ParticleNet cut, so every cutflow that does not
involve ParticleNet must come out identical. Any difference there means
something other than the model changed and the PNet comparison is not clean.

Chunk sizes differ between the runs (20 files per chunk for the v10 backgrounds,
5 or fewer for v11, since ParticleNet dominates the cost), so only the hadded
totals are comparable, not the per-chunk files.

Usage: chk_pnetv11.py [old_dir] [new_dir]
"""
import os
import sys

import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kFatal

SAMPLES = ['ecal_pn_v15_8gev', 'ecal_conversion_v15_8gev',
           'target_pn_v15_8gev', 'target_conversion_v15_8gev',
           'signal_v15_8gev_0.001', 'signal_v15_8gev_0.01',
           'signal_v15_8gev_0.1', 'signal_v15_8gev_1.0']
# every flow that must be untouched by the model change
SAME = ['StdCutFlowWithTracking_RecoilX', 'CnCCutFlow_RecoilX',
        'StdCutFlow_RecoilX', 'BDTCutFlow_RecoilX']
PNET = 'PNetCutFlow_RecoilX'


def flow(d, stem, hname):
    p = '%s/%s_histos.root' % (d, stem)
    if not os.path.exists(p):
        return None
    f = ROOT.TFile.Open(p)
    if not f or f.IsZombie():
        return None
    dd = f.Get('CutBasedDM')
    h = dd.Get(hname) if dd else None
    if not h:
        f.Close()
        return None
    px = h.ProjectionX()
    v = [px.GetBinContent(i + 1) for i in range(px.GetNbinsX())]
    f.Close()
    return v


def main():
    old = sys.argv[1] if len(sys.argv) > 1 else 'analysis'
    new = sys.argv[2] if len(sys.argv) > 2 else 'analysis_pnetv11'

    print('== cutflows that must be identical (%s vs %s) ==' % (old, new))
    bad = 0
    for s in SAMPLES:
        for h in SAME:
            a, b = flow(old, s, h), flow(new, s, h)
            if a is None or b is None:
                print('  %-28s %-32s MISSING %s' %
                      (s, h, old if a is None else new))
                continue
            if a == b:
                continue
            # the conversion samples ran without PNet in the v10 tree, but that
            # only blanks the PNet flow, so a difference here is still real
            diffs = [(i, x, y) for i, (x, y) in enumerate(zip(a, b)) if x != y]
            print('  %-28s %-32s DIFFERS in %d bins, first %r' %
                  (s, h, len(diffs), diffs[:3]))
            bad += 1
    print('  %s' % ('all identical' if bad == 0 else '%d MISMATCHES' % bad))

    print()
    print('== ParticleNet flow, v10 -> v11 ==')
    labels = ['acceptance', 'trigger', 'loosePresel', 'pnet', 'hcalMaxPE<8']
    print('%-28s %-13s %12s %12s' % ('sample', 'cut', old, new))
    for s in SAMPLES:
        a, b = flow(old, s, PNET), flow(new, s, PNET)
        if b is None:
            print('  %-26s %s' % (s, 'no v11 output yet'))
            continue
        for i, lab in enumerate(labels):
            av = '%12.0f' % a[i] if a else '%12s' % '--'
            print('%-28s %-13s %s %12.0f' % (s if i == 0 else '', lab, av, b[i]))


if __name__ == '__main__':
    main()
