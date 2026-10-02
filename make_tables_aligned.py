#!/usr/bin/env python3
"""BDT, cut-and-count and ParticleNet tables with aligned non-ECal cuts.

All three now apply: trigger, at least one ECal hit, tracker veto,
N_straight < 3, HCal maxPE < 8. They differ only in the ECal selection.

  BDT   StdCutFlowWithTracking (the hit requirement is inside its preselection row)
  CnC   CnCAlignedCutFlow_RecoilX
  PNet  PNetAlignedCutFlow_RecoilX, plus a threshold scan on PNetAlignedDiscPostAll

Signal efficiency uses one convention for all three: trigger efficiency times
N(pass) / N(acceptance). Backgrounds at 1.5e14 EoT.

Usage: make_tables_aligned.py [--ana DIR]
"""
import glob
import os
import sys

import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kFatal

ANA = sys.argv[sys.argv.index('--ana') + 1] if '--ana' in sys.argv else 'analysis_aligned'
sys.stderr.write('reading %s/\n' % ANA)

TGT = 1.5e14
PRES = '/sdf/data/ldmx/private_production/mc26/pres_skim/'
RECO = '/sdf/data/ldmx/private_production/mc26/reco_v492/'
BKGS = [('ecal_pn_v15_8gev', r'\ecal PN', 1.5e14),
        ('ecal_conversion_v15_8gev', r'\ecal conv.', 1.0e15),
        ('target_pn_v15_8gev', 'Target PN', 1.0e15),
        ('target_conversion_v15_8gev', 'Target conv.', 1.0e15)]
SIGS = [('signal_v15_8gev_0.001', r'1\MeV', 0.8641),
        ('signal_v15_8gev_0.01', r'10\MeV', 0.8578),
        ('signal_v15_8gev_0.1', r'100\MeV', 0.8672),
        ('signal_v15_8gev_1.0', r'1000\MeV', 0.8648)]
NTRIG = {'ecal_pn_v15_8gev': 2.116e8, 'ecal_conversion_v15_8gev': 8.046e7,
         'target_pn_v15_8gev': 7.118e5, 'target_conversion_v15_8gev': 5.572e6}
SHIPPED = 0.5664


def coverage(stem):
    ni = len(glob.glob(PRES + stem + '/*.root'))
    no = len(glob.glob(RECO + stem + '/*_reco.root'))
    return float(ni) / no if (ni and no) else 1.0


WEIGHT = {s: TGT / e * coverage(s) for s, _, e in BKGS}


def get(stem, name):
    p = '%s/%s_histos.root' % (ANA, stem)
    f = ROOT.TFile.Open(p)
    if not f or f.IsZombie():
        raise SystemExit('cannot open %s' % p)
    h = f.Get('CutBasedDM').Get(name)
    if not h:
        raise SystemExit('no %s in %s' % (name, p))
    h = h.Clone('%s_%s' % (stem, name))
    h.SetDirectory(0)
    f.Close()
    return h


def flow(stem, name):
    px = get(stem, name).ProjectionX()
    return [px.GetBinContent(i + 1) for i in range(px.GetNbinsX())], \
        [px.GetXaxis().GetBinLabel(i + 1) for i in range(px.GetNbinsX())]


def bkgcell(x):
    return r'$<$1' if x < 1 else '{:,.0f}'.format(x)


def table(title, name, rows, trig_row=None):
    """rows: list of (bin index, label). trig_row: bin whose bkg value comes from NTRIG."""
    data = {s: flow(s, name)[0] for s, _, _ in BKGS + [(x[0], x[1], 0) for x in SIGS]}
    out = ['%%%%%% %s, aligned non-ECal cuts' % title]
    for idx, lab in rows:
        cells = []
        for s, _, _ in BKGS:
            v = NTRIG[s] if idx == trig_row else data[s][idx]
            cells.append(bkgcell(v * WEIGHT[s]))
        for s, _, trig in SIGS:
            v = data[s]
            cells.append('{:.1f}\\%'.format(100.0 * trig * v[idx] / v[0]))
        out.append('%-30s & %s \\\\ \\hline' % (lab, ' & '.join(cells)))
    return out, data


def scan():
    hb = get('ecal_pn_v15_8gev', 'PNetAlignedDiscPostAll')
    sig = {s: get(s, 'PNetAlignedDiscPostAll') for s, _, _ in SIGS}
    den = {s: flow(s, 'PNetAlignedCutFlow_RecoilX')[0][0] for s, _, _ in SIGS}
    w = WEIGHT['ecal_pn_v15_8gev']

    def above(h, cut):
        return h.Integral(h.GetXaxis().FindBin(cut + 1e-9), h.GetNbinsX() + 1)

    out = ['%%%%%% ParticleNet threshold scan, aligned flow (0.001 bins)',
           '%% %-8s %10s %6s   %s' % ('cut', 'ECal PN', 'raw',
                                      '  '.join('%8s' % l for _, l, _ in SIGS))]
    cuts = [SHIPPED] + [round(0.05 * k, 3) for k in range(0, 20)] + \
        [0.96, 0.97, 0.98, 0.99, 0.995, 0.999]
    for c in cuts:
        nb = above(hb, c)
        effs = ['%7.1f%%' % (100 * trig * above(sig[s], c) / den[s]) for s, _, trig in SIGS]
        out.append('%% %-8.4f %10.2f %6.0f   %s%s' % (
            c, nb * w, nb, '  '.join(effs), '   <- shipped' if c == SHIPPED else ''))
    # loosest threshold with at most one event, scanning upward bin by bin
    for i in range(1, hb.GetNbinsX() + 1):
        c = hb.GetXaxis().GetBinLowEdge(i)
        if above(hb, c) * w <= 1.0:
            effs = [100 * trig * above(sig[s], c) / den[s] for s, _, trig in SIGS]
            out.append('%% loosest cut with <= 1 ECal PN event: disc > %.3f, %.2f events, '
                       'signal %s' % (c, above(hb, c) * w,
                                      ' / '.join('%.1f%%' % e for e in effs)))
            break
    return out


def main():
    bdt, bd = table('BDT (Humberto)', 'StdCutFlowWithTracking_RecoilX',
                    [(2, 'Triggered'), (3, r'Pre-selection, \ecal hits $\geq$ 1'),
                     (4, 'Tracker veto'), (5, 'Ecal veto (BDT)'),
                     (6, r'$N_{straight} < 3$'), (7, r'HCal maxPE $<$ 8')],
                    trig_row=2)
    cnc_labels = flow('ecal_pn_v15_8gev', 'CnCAlignedCutFlow_RecoilX')[1]
    cnc, cd = table('cut and count', 'CnCAlignedCutFlow_RecoilX',
                    [(i, cnc_labels[i].replace('>=', r'$\geq$')) for i in range(13)])
    pn_labels = flow('ecal_pn_v15_8gev', 'PNetAlignedCutFlow_RecoilX')[1]
    pnet, pd = table('ParticleNet v11', 'PNetAlignedCutFlow_RecoilX',
                     [(i, pn_labels[i].replace('>=', r'$\geq$')) for i in range(8)])
    for block in (bdt, cnc, pnet, scan()):
        print('\n'.join(block))
        print()

    print('%%%%%% summary: total background after the last cut, signal efficiency')
    for lab, data, last in (('BDT', bd, 7), ('CnC', cd, 12), ('PNet', pd, 7)):
        b = sum(data[s][last] * WEIGHT[s] for s, _, _ in BKGS)
        e = ' / '.join('%.1f%%' % (100 * trig * data[s][last] / data[s][0])
                       for s, _, trig in SIGS)
        print('%% %-5s background %6.2f   signal %s' % (lab, b, e))


if __name__ == '__main__':
    main()
