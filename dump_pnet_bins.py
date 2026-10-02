#!/usr/bin/env python3
"""PNetCutFlow bin contents of the existing histograms.

Bins 0 to 2 (acceptance, trigger, loose PNet preselection) do not involve the
model, so they say how many events a v11 run would actually have to evaluate
ParticleNet on if the loose cut were applied first.
"""
import glob
import os
import sys

import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kFatal


def bins(path, name='PNetCutFlow_RecoilX'):
    f = ROOT.TFile.Open(path)
    if not f or f.IsZombie():
        return None
    d = f.Get('CutBasedDM')
    h = d.Get(name) if d else None
    if not h:
        f.Close()
        return None
    px = h.ProjectionX()
    v = [px.GetBinContent(i + 1) for i in range(px.GetNbinsX())]
    f.Close()
    return v


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else 'analysis'
    print('%-34s %12s %12s %12s %12s %12s  %8s' %
          ('sample', 'accept', 'trigger', 'loosePres', 'pnet', 'hcal', 'pres/trig'))
    for p in sorted(glob.glob(os.path.join(d, '*_histos.root'))):
        if 'signal_mass' in p:
            continue
        v = bins(p)
        if not v:
            continue
        frac = (v[2] / v[1]) if v[1] else 0.0
        print('%-34s %12.0f %12.0f %12.0f %12.0f %12.0f  %7.3f%%'
              % (os.path.basename(p)[:-12], v[0], v[1], v[2], v[3], v[4],
                 100 * frac))


if __name__ == '__main__':
    main()
