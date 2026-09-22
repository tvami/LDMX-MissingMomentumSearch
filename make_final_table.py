#!/usr/bin/env python3
"""Final v15 cutflow table, every column normalized to a common 1.5e14 EoT.

Two things do not come from the cutflow histograms:

  Triggered  the four skimmed samples are 100% trigger-pass by construction, so
             their trigger row is counted from mc26/trigger_skim instead. EN is
             not trigger skimmed, so its trigger row is a real cutflow bin.
  Acceptance backgrounds are counted regardless of acceptance (100%); signal is
             the truth acceptance from the Acceptance histogram.

"<1" means zero events survived. That is only honest when one observed event
weighs less than 1 after scaling, so the weight is printed for every column.
"""
import os
import sys

import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kWarning

TARGET_EOT = 1.5e14
CUTFLOW = 'StdCutFlowWithTracking_RecoilX'
PRES = '/sdf/data/ldmx/private_production/mc26/pres_skim/'
RECO = '/sdf/data/ldmx/private_production/mc26/reco_v492/'

# label, histo stem, sample EoT, pres_skim subdir for coverage (None = no
# coverage correction), trigger_skim event count (None = use cutflow bin 2)
BKGS = [
    ('Target PN',    'target_pn_v15_8gev',         1.0e15, 'target_pn_v15_8gev',         7.118e5),
    ('Target conv.', 'target_conversion_v15_8gev', 1.0e15, 'target_conversion_v15_8gev', 5.572e6),
    ('Target EN',    'targetEN_GENIE_G21_11b_00_000_v15_ti_8gev', 1.5e14, None, None),
    (r'\ecal PN',    'ecal_pn_v15_8gev',           1.5e14, 'ecal_pn_v15_8gev',           2.116e8),
    (r'\ecal conv.', 'ecal_conversion_v15_8gev',   1.0e15, 'ecal_conversion_v15_8gev',   8.046e7),
]
SIGS = [(r'1\MeV', 'signal_v15_8gev_0.001'), (r'10\MeV', 'signal_v15_8gev_0.01'),
        (r'100\MeV', 'signal_v15_8gev_0.1'), (r'1000\MeV', 'signal_v15_8gev_1.0')]
ROWS = [(2, 'Triggered'), (3, 'Pre-selection skim'), (4, 'Tracker veto'),
        (5, 'Ecal veto'), (6, r'$N_{straight} < 3$'), (7, r'HCal maxPE $<$ 8')]


def _hist(path, name):
    if not os.path.exists(path):
        return None
    f = ROOT.TFile.Open(path)
    if not f or f.IsZombie():
        return None
    d = f.Get('CutBasedDM')
    h = d.Get(name) if d else None
    if not h:
        f.Close()
        return None
    px = h.ProjectionX()
    vals = [px.GetBinContent(i + 1) for i in range(px.GetNbinsX())]
    f.Close()
    return vals


def coverage(sub):
    import glob
    if not sub:
        return 1.0
    ni = len(glob.glob(PRES + sub + '/*.root'))
    no = len(glob.glob(RECO + sub + '/*_reco.root'))
    return (float(ni) / no) if (ni and no) else 1.0


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else 'analysis'
    out, notes = [], []

    bkg = {}
    for label, stem, eot, sub, ntrig in BKGS:
        vals = _hist(os.path.join(d, stem + '_histos.root'), CUTFLOW)
        w = TARGET_EOT / eot * coverage(sub)
        bkg[label] = (vals, w, ntrig)
        notes.append('%% %-14s EoT=%.2e  weight/event=%.4f  "<1" %s'
                     % (label, eot, w, 'ok' if w < 1.0001 else 'MISLEADING'))

    sig = {lab: _hist(os.path.join(d, stem + '_histos.root'), CUTFLOW) for lab, stem in SIGS}
    acc = {}
    for lab, stem in SIGS:
        a = _hist(os.path.join(d, stem + '_histos.root'), 'Acceptance')
        acc[lab] = (a[5] / a[0]) if (a and a[0] > 0) else None

    # Acceptance row
    cells = ['100.0\\%'] * len(BKGS)
    cells += ['{:.1f}\\%'.format(100 * acc[l]) if acc[l] else '--' for l, _ in SIGS]
    out.append('%-22s & %s \\\\ \\hline' % ('Acceptance', '\n& '.join(cells)))

    for idx, row in ROWS:
        cells = []
        for label, _, _, _, ntrig in BKGS:
            vals, w, nt = bkg[label]
            if not vals:
                cells.append('--')
                continue
            v = (nt if (idx == 2 and nt) else vals[idx]) * w
            cells.append(r'$<$1' if v < 1 else '{:,.0f}'.format(v))
        for lab, _ in SIGS:
            v = sig[lab]
            cells.append('{:.1f}\\%'.format(100.0 * v[idx] / v[3]) if (v and v[3] > 0) else '--')
        out.append('%-22s & %s \\\\ \\hline' % (row, '\n& '.join(cells)))

    print('\n'.join(out))
    print()
    print('\n'.join(notes))
    for label, _, _, _, _ in BKGS:
        vals, w, nt = bkg[label]
        if vals:
            print('%% %-14s raw %s' % (label, ' '.join('%d:%.0f' % (i, vals[i]) for i, _ in ROWS)))


if __name__ == '__main__':
    main()
