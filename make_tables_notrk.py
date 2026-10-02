#!/usr/bin/env python3
"""The three selections with and without the tracker veto, from one tree.

Both use identical non-ECal cuts for all three selections, so they compare like
for like; the only difference between the two blocks is the tracker veto.

  with      StdCutFlowWithTracking, CnCAlignedCutFlow, PNetAlignedCutFlow
  without   BDTNoTrkCutFlow, CnCCutFlow, PNetNoTrkCutFlow
            (CnCCutFlow already has no tracker veto, and its N_hits row carries
            the ECal hit requirement)

The "with" block must reproduce make_tables_aligned.py on analysis_aligned/
exactly; it is printed here as that cross-check.

Usage: make_tables_notrk.py [--ana DIR]
"""
import glob
import sys

import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kFatal

ANA = sys.argv[sys.argv.index('--ana') + 1] if '--ana' in sys.argv else 'analysis_notrk'
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
SHIPPED = 0.5664

# (label, flow histogram, index of its last bin)
WITH = [('BDT', 'StdCutFlowWithTracking_RecoilX', 7),
        ('CnC', 'CnCAlignedCutFlow_RecoilX', 12),
        ('PNet', 'PNetAlignedCutFlow_RecoilX', 7)]
WITHOUT = [('BDT', 'BDTNoTrkCutFlow_RecoilX', 5),
           ('CnC', 'CnCCutFlow_RecoilX', 10),
           ('PNet', 'PNetNoTrkCutFlow_RecoilX', 6)]


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


def full_table(title, name):
    vals = {s: flow(s, name)[0] for s, _, _ in BKGS + [(x[0], x[1], 0) for x in SIGS]}
    labels = flow('ecal_pn_v15_8gev', name)[1]
    out = ['%%%%%% %s, no tracker veto' % title]
    for i, lab in enumerate(labels):
        cells = []
        for s, _, _ in BKGS:
            x = vals[s][i] * WEIGHT[s]
            cells.append(r'$<$1' if x < 1 else '{:,.0f}'.format(x))
        for s, _, trig in SIGS:
            v = vals[s]
            cells.append('{:.1f}\\%'.format(100.0 * trig * v[i] / v[0]))
        out.append('%-30s & %s \\\\ \\hline' % (lab.replace('>=', r'$\geq$'), ' & '.join(cells)))
    return out


def summary(block, title):
    out = ['%%%%%% %s: ECal PN, all backgrounds, signal efficiency' % title]
    for lab, name, last in block:
        d = {s: flow(s, name)[0] for s, _, _ in BKGS + [(x[0], x[1], 0) for x in SIGS]}
        epn = d['ecal_pn_v15_8gev'][last] * WEIGHT['ecal_pn_v15_8gev']
        tot = sum(d[s][last] * WEIGHT[s] for s, _, _ in BKGS)
        per = ' '.join('%s %.2f' % (s.split('_v15')[0], d[s][last] * WEIGHT[s])
                       for s, _, _ in BKGS[1:])
        e = ' / '.join('%.1f%%' % (100 * trig * d[s][last] / d[s][0]) for s, _, trig in SIGS)
        out.append('%% %-5s ECal PN %6.2f   all %6.2f   signal %s   [%s]'
                   % (lab, epn, tot, e, per))
    return out


def scan(hname, den_flow, title):
    hb = get('ecal_pn_v15_8gev', hname)
    sig = {s: get(s, hname) for s, _, _ in SIGS}
    den = {s: flow(s, den_flow)[0][0] for s, _, _ in SIGS}
    w = WEIGHT['ecal_pn_v15_8gev']

    def above(h, c):
        return h.Integral(h.GetXaxis().FindBin(c + 1e-9), h.GetNbinsX() + 1)

    out = ['%%%%%% %s (0.001 bins)' % title]
    for c in [SHIPPED, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9]:
        out.append('%% %-7.4f ECal PN %6.2f   signal %s' % (
            c, above(hb, c) * w,
            ' / '.join('%.1f%%' % (100 * t * above(sig[s], c) / den[s]) for s, _, t in SIGS)))
    for i in range(1, hb.GetNbinsX() + 1):
        c = hb.GetXaxis().GetBinLowEdge(i)
        if above(hb, c) * w <= 1.0:
            out.append('%% loosest cut with <= 1 ECal PN event: disc > %.3f, %.2f events, signal %s'
                       % (c, above(hb, c) * w,
                          ' / '.join('%.1f%%' % (100 * t * above(sig[s], c) / den[s])
                                     for s, _, t in SIGS)))
            break
    return out


def main():
    blocks = [full_table('BDT (Humberto)', 'BDTNoTrkCutFlow_RecoilX'),
              full_table('cut and count', 'CnCCutFlow_RecoilX'),
              full_table('ParticleNet v11', 'PNetNoTrkCutFlow_RecoilX'),
              scan('PNetNoTrkDiscPostAll', 'PNetNoTrkCutFlow_RecoilX',
                   'ParticleNet threshold scan, no tracker veto'),
              summary(WITH, 'WITH tracker veto (must match tables_aligned.tex)'),
              summary(WITHOUT, 'WITHOUT tracker veto')]
    for b in blocks:
        print('\n'.join(b))
        print()


if __name__ == '__main__':
    main()
