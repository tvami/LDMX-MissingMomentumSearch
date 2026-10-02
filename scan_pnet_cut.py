#!/usr/bin/env python3
"""Where does ParticleNet reach one background event, and at what signal cost?

Scans the ParticleNet threshold on the disc distribution of events that already
passed the HCal veto, so the yield quoted is the final one. Reports the scan
twice: as it stands, and with events that have no ECal readout hits removed.

Those zero-hit events pass every cut in the flow for free, because every cut is
an upper bound, and an empty ECal reads as maximally signal-like to the network,
so they land at disc = 1 and cannot be cut away by any threshold.

Also prints what the survivors of both flows are made of, from the N_hits
distribution at the last stage of each.
"""
import sys

import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kFatal

ANA = sys.argv[1] if len(sys.argv) > 1 else 'analysis_nhits'
BKG = 'ecal_pn_v15_8gev'
BKG_SCALE = 6172.0 / 5921.0        # 1.5e14 EoT sample, coverage only
SIGS = [('signal_v15_8gev_0.001', '1 MeV', 0.8641),
        ('signal_v15_8gev_0.01', '10 MeV', 0.8578),
        ('signal_v15_8gev_0.1', '100 MeV', 0.8672),
        ('signal_v15_8gev_1.0', '1000 MeV', 0.8648)]
SHIPPED = 0.5664


def get(stem, name):
    f = ROOT.TFile.Open('%s/%s_histos.root' % (ANA, stem))
    if not f or f.IsZombie():
        raise SystemExit('cannot open %s' % stem)
    h = f.Get('CutBasedDM').Get(name)
    if not h:
        raise SystemExit('no %s in %s' % (name, stem))
    h = h.Clone('%s_%s' % (stem, name))
    h.SetDirectory(0)
    f.Close()
    return h


def above(h, cut):
    lo = h.GetXaxis().FindBin(cut + 1e-9)
    return h.Integral(lo, h.GetNbinsX() + 1)


def denom(stem):
    """Events in acceptance, the denominator of the efficiency convention."""
    h = get(stem, 'PNetCutFlow_RecoilX')
    return h.ProjectionX().GetBinContent(1)


def scan(hname, label):
    hb = get(BKG, hname)
    sig = {lab: get(stem, hname) for stem, lab, _ in SIGS}
    den = {lab: denom(stem) for stem, lab, _ in SIGS}

    print()
    print('== %s ==' % label)
    print('ECal PN after the HCal veto, before any PNet cut: %.0f raw, %.1f scaled'
          % (hb.Integral(0, hb.GetNbinsX() + 1),
             hb.Integral(0, hb.GetNbinsX() + 1) * BKG_SCALE))
    print('%-10s %12s %10s %s' % ('cut', 'ECal PN', 'raw', '   '.join(
        '%9s' % lab for _, lab, _ in SIGS)))

    # the shipped point, then the scan
    cuts = [SHIPPED] + [hb.GetXaxis().GetBinLowEdge(i)
                        for i in range(1, hb.GetNbinsX() + 1)]
    shown = 0
    one_point = None
    for cut in cuts:
        nb = above(hb, cut) * BKG_SCALE
        effs = []
        for stem, lab, trig in SIGS:
            e = trig * above(sig[lab], cut) / den[lab] if den[lab] else 0.0
            effs.append(100 * e)
        is_shipped = (cut == SHIPPED)
        if one_point is None and nb <= 1.0 and not is_shipped:
            one_point = (cut, nb, list(effs))
        if is_shipped or (shown < 14 and cut >= 0.5 and cut <= 1.01
                          and round(cut * 100) % 5 == 0):
            tag = '  <- shipped' if is_shipped else ''
            print('%-10.4f %12.1f %10.0f %s%s'
                  % (cut, nb, above(hb, cut),
                     '   '.join('%8.1f%%' % e for e in effs), tag))
            shown += 1

    if one_point:
        cut, nb, effs = one_point
        print()
        print('ONE EVENT at disc > %.3f : %.2f ECal PN events, signal %s'
              % (cut, nb, ' / '.join('%.1f%%' % e for e in effs)))
    else:
        print()
        print('NO threshold reaches one event: the floor is %.1f events'
              % (above(hb, 1.0) * BKG_SCALE))


def survivors():
    print()
    print('== what the survivors are made of ==')
    for hname, nstage, lab in [('PNetCutFlow_NHits', 4, 'ParticleNet'),
                               ('CnCCutFlow_NHits', 10, 'cut and count')]:
        h = get(BKG, hname)
        py = h.ProjectionY('surv_%s' % hname, nstage + 1, nstage + 1)
        tot = py.Integral(0, py.GetNbinsX() + 1)
        zero = py.GetBinContent(1)
        print('%-15s ECal PN survivors: %.0f raw (%.1f scaled), of which '
              'N_hits = 0: %.0f (%.0f%%)'
              % (lab, tot, tot * BKG_SCALE, zero,
                 100 * zero / tot if tot else 0))


def main():
    scan('PNetDiscPostHcal', 'as it stands')
    scan('PNetDiscPostHcalWithHit', 'with zero-ECal-hit events removed')
    survivors()


if __name__ == '__main__':
    main()
