#!/usr/bin/env python3
"""BDT, cut-and-count and ParticleNet tables with at least one ECal hit required.

Exact, no re-run: every flow has a histogram of N_hits at each stage, so
"stage i AND N_hits >= 1" is the stage total minus its N_hits = 0 bin. The
requirement is shown as its own row after preselection (BDT) or the trigger
(CnC, PNet), then applied to every row below it.

  BDT       StdCutFlowWithTracking + NReadoutHits, from analysis_pnetv11 (all samples)
  CnC/PNet  CnCCutFlow_NHits / PNetCutFlow_NHits, from analysis_nhits (ECal PN and
            signal). The other backgrounds were not re-run with those histograms;
            ECal conv. and Target conv. have no zero-hit events at all, Target PN
            has 7, so their columns are taken as they stand (footnote in the output)

Usage: make_tables_withhit.py [--full DIR] [--nhits DIR]
"""
import glob
import os
import sys

import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kFatal


def arg(name, default):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


FULL = arg('--full', 'analysis_pnetv11')
NHITS = arg('--nhits', 'analysis_nhits')
sys.stderr.write('full tree %s/, N_hits tree %s/\n' % (FULL, NHITS))

TGT = 1.5e14
PRES = '/sdf/data/ldmx/private_production/mc26/pres_skim/'
RECO = '/sdf/data/ldmx/private_production/mc26/reco_v492/'
# stem, label, EoT
BKGS = [('ecal_pn_v15_8gev', r'\ecal PN', 1.5e14),
        ('ecal_conversion_v15_8gev', r'\ecal conv.', 1.0e15),
        ('target_pn_v15_8gev', 'Target PN', 1.0e15),
        ('target_conversion_v15_8gev', 'Target conv.', 1.0e15)]
SIGS = [('signal_v15_8gev_0.001', r'1\MeV', 0.8641),
        ('signal_v15_8gev_0.01', r'10\MeV', 0.8578),
        ('signal_v15_8gev_0.1', r'100\MeV', 0.8672),
        ('signal_v15_8gev_1.0', r'1000\MeV', 0.8648)]
# trigger-skim counts for the Triggered row of the BDT table, as in make_final_table.py
NTRIG = {'ecal_pn_v15_8gev': 2.116e8, 'ecal_conversion_v15_8gev': 8.046e7,
         'target_pn_v15_8gev': 7.118e5, 'target_conversion_v15_8gev': 5.572e6}


def coverage(stem):
    ni = len(glob.glob(PRES + stem + '/*.root'))
    no = len(glob.glob(RECO + stem + '/*_reco.root'))
    return float(ni) / no if (ni and no) else 1.0


WEIGHT = {s: TGT / e * coverage(s) for s, _, e in BKGS}


def open_dir(tree, stem):
    p = '%s/%s_histos.root' % (tree, stem)
    if not os.path.exists(p):
        return None, None
    f = ROOT.TFile.Open(p)
    return f, f.Get('CutBasedDM')


def flow_and_zero(tree, stem, flow, nhits, nstage):
    """Per stage: total, and how many of those have N_hits = 0."""
    f, d = open_dir(tree, stem)
    if not d or not d.Get(flow) or not d.Get(nhits):
        if f:
            f.Close()
        return None, None
    px = d.Get(flow).ProjectionX('px_%s_%s' % (stem, flow))
    h2 = d.Get(nhits)
    tot, zero = [], []
    for i in range(nstage):
        tot.append(px.GetBinContent(i + 1))
        py = h2.ProjectionY('py_%s_%s_%d' % (stem, nhits, i), i + 1, i + 1)
        zero.append(py.GetBinContent(1))
    f.Close()
    return tot, zero


def bkgcell(x):
    return r'$<$1' if x < 1 else '{:,.0f}'.format(x)


def row(label, cells):
    return '%-30s & %s \\\\ \\hline' % (label, ' & '.join(cells))


def bdt_table():
    """Standard flow: 0 All, 1 Fiducial, 2 Trig, 3 Presel, 4 Tracker, 5 ECal (BDT), 6 MIP, 7 HCal."""
    nst = 8
    data = {s: flow_and_zero(FULL, s, 'StdCutFlowWithTracking_RecoilX', 'NReadoutHits', nst)
            for s, _, _ in BKGS + [(x[0], x[1], 0) for x in SIGS]}
    names = [(2, 'Triggered'), (3, 'Pre-selection skim'), ('hit', r'\ecal hits $\geq$ 1'),
             (4, 'Tracker veto'), (5, 'Ecal veto'), (6, r'$N_{straight} < 3$'),
             (7, r'HCal maxPE $<$ 8')]
    out = ['%%%%%% BDT (Humberto), at least one ECal hit required']
    for idx, lab in names:
        cells = []
        for s, _, _ in BKGS:
            tot, zero = data[s]
            if tot is None:
                cells.append('--')
                continue
            if idx == 2:
                v = NTRIG[s]
            elif idx == 3:
                v = tot[3]
            elif idx == 'hit':
                v = tot[3] - zero[3]
            else:
                v = tot[idx] - zero[idx]
            cells.append(bkgcell(v * WEIGHT[s]))
        for s, _, _ in SIGS:
            tot, zero = data[s]
            den = tot[3]
            if idx in (2, 3):
                num = tot[idx]
            elif idx == 'hit':
                num = tot[3] - zero[3]
            else:
                num = tot[idx] - zero[idx]
            cells.append('{:.1f}\\%'.format(100.0 * num / den))
        out.append(row(lab, cells))
    return out, data


def ml_table(flow, nhits, nst, labels, bkgs, title):
    """CnC or PNet: rows 0 acceptance, 1 trigger, then the hit row, then 2.. with the hit cut."""
    out = ['%%%%%% %s, at least one ECal hit required' % title]
    data, notes = {}, []
    for s, _, _ in bkgs:
        tot, zero = flow_and_zero(NHITS, s, flow, nhits, nst)
        if tot is None:
            # not re-run with the N_hits histograms: take the flow as it stands
            f, d = open_dir(FULL, s)
            px = d.Get(flow).ProjectionX('px_full_%s_%s' % (s, flow))
            tot = [px.GetBinContent(i + 1) for i in range(nst)]
            f.Close()
            zero = [0.0] * nst
            notes.append(s)
        data[s] = (tot, zero)
    for s, _, _ in SIGS:
        data[s] = flow_and_zero(NHITS, s, flow, nhits, nst)

    order = [(0, labels[0]), (1, labels[1]), ('hit', r'\ecal hits $\geq$ 1')] + \
            [(i, labels[i]) for i in range(2, nst)]
    for idx, lab in order:
        cells = []
        for s, _, _ in bkgs:
            tot, zero = data[s]
            if idx in (0, 1):
                v = tot[idx]
            elif idx == 'hit':
                v = tot[1] - zero[1]
            else:
                v = tot[idx] - zero[idx]
            cells.append(bkgcell(v * WEIGHT[s]))
        for s, _, trig in SIGS:
            tot, zero = data[s]
            if idx in (0, 1):
                num = tot[idx]
            elif idx == 'hit':
                num = tot[1] - zero[1]
            else:
                num = tot[idx] - zero[idx]
            cells.append('{:.1f}\\%'.format(100.0 * trig * num / tot[0]))
        out.append(row(lab, cells))
    if notes:
        out.append('%% taken as they stand (not re-run with N_hits histograms): '
                   + ', '.join(notes))
    return out, data


def main():
    bdt, bdata = bdt_table()
    cnc, cdata = ml_table(
        'CnCCutFlow_RecoilX', 'CnCCutFlow_NHits', 11,
        ['All / Acceptance', 'Triggered', r'$E_\mathrm{sum} < 3500$',
         r'$E_\mathrm{sumTight} < 800$', r'$E_\mathrm{back} < 250$',
         r'$N_\mathrm{hits} < 70$', r'$\mathrm{RMS}_\mathrm{shower} < 110$',
         r'$E_\mathrm{cell,max} < 300$', r'$\mathrm{RMS}_\mathrm{Layer,hit} < 5$',
         r'$N_\mathrm{straight} < 3$', r'HCal maxPE $< 8$'],
        BKGS[:2], 'cut and count')
    pnet, pdata = ml_table(
        'PNetCutFlow_RecoilX', 'PNetCutFlow_NHits', 5,
        ['All / Acceptance', 'Triggered', 'Preselection', 'ParticleNet v11',
         r'HCal maxPE $< 8$'],
        BKGS, 'ParticleNet')
    for block in (bdt, cnc, pnet):
        print('\n'.join(block))
        print()

    # one-line comparison, all in the CnC/PNet convention (x trigger efficiency)
    print('%%%%%% final yields and signal efficiency, CnC/PNet convention')
    tot, zero = bdata['ecal_pn_v15_8gev']
    print('%% BDT   ECal PN %.2f   eff %s' % (
        (tot[7] - zero[7]) * WEIGHT['ecal_pn_v15_8gev'],
        ' / '.join('%.1f%%' % (100 * trig * (bdata[s][0][7] - bdata[s][1][7]) / bdata[s][0][3])
                   for s, _, trig in SIGS)))
    for lab, data, last in (('CnC', cdata, 10), ('PNet', pdata, 4)):
        tot, zero = data['ecal_pn_v15_8gev']
        print('%% %-5s ECal PN %.2f   eff %s' % (
            lab, (tot[last] - zero[last]) * WEIGHT['ecal_pn_v15_8gev'],
            ' / '.join('%.1f%%' % (100 * trig * (data[s][0][last] - data[s][1][last]) / data[s][0][0])
                       for s, _, trig in SIGS)))


if __name__ == '__main__':
    main()
