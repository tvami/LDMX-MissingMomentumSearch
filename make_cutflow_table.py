#!/usr/bin/env python3
"""Build the LaTeX cutflow table from the hadded CutBasedDM histograms.

Backgrounds are scaled to the EoT equivalent in the table header:
    scale = target_EoT / sample_EoT
Verified against the previous table: predicting its preselection row from
pres_skim file counts and measured events/file reproduces target PN, target
conversion and ecal PN to within 2%.

Signal efficiencies are quoted relative to the preselection row, which is how
the previous table defined them (preselection = 100%).

Usage:
    python3 make_cutflow_table.py <dir with <sample>_histos.root>
"""
import os
import sys

import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kWarning

CUTFLOW = 'StdCutFlowWithTracking_RecoilX'

# bin index in the cutflow -> table row label
ROWS = [
    (2, 'Triggered'),
    (3, 'Pre-selection skim'),
    (4, 'Tracker veto'),
    (5, 'Ecal veto'),
    (6, r'$N_{straight} < 3$'),
    (7, r'HCal maxPE $<$ 8'),
]

PRES = '/sdf/data/ldmx/private_production/mc26/pres_skim/'
RECO = '/sdf/data/ldmx/private_production/mc26/reco_v492/'


def coverage(sub):
    """total pres_skim inputs / reco files actually produced.

    Some inputs are irrecoverable (their pres_skim file is missing a RunHeader
    for its very first run, so conditions never initialise). Backgrounds are
    quoted at a fixed EoT, so the survivors must be scaled up by the fraction
    of the sample that was reconstructed, otherwise every background column is
    silently low by that fraction.
    """
    import glob
    ni = len(glob.glob(PRES + sub + '/*.root'))
    no = len(glob.glob(RECO + sub + '/*_reco.root'))
    return (float(ni) / no if no else None), ni, no


# label, file stem, sample EoT equivalent, EoT the column is quoted at
BKGS = [
    ('Target PN',    'target_pn_v15_8gev',         1.0e15, 1.0e15),
    ('Target conv.', 'target_conversion_v15_8gev', 1.0e15, 1.0e15),
    ('Target EN',    'targetEN_GENIE_G21_11b_00_000_v15_ti_8gev', None, 1.0e16),
    (r'\ecal PN',    'ecal_pn_v15_8gev',           1.5e14, 5.0e13),
    (r'\ecal conv.', 'ecal_conversion_v15_8gev',   1.0e15, 1.0e15),
]

SIGS = [
    (r'1\MeV',    'signal_v15_8gev_0.001'),
    (r'10\MeV',   'signal_v15_8gev_0.01'),
    (r'100\MeV',  'signal_v15_8gev_0.1'),
    (r'1000\MeV', 'signal_v15_8gev_1.0'),
]


def acceptance_frac(path):
    """Signal truth acceptance = Acceptance/All from the Acceptance histogram."""
    if not os.path.exists(path):
        return None
    f = ROOT.TFile.Open(path)
    if not f or f.IsZombie():
        return None
    d = f.Get('CutBasedDM')
    h = d.Get('Acceptance') if d else None
    if not h:
        f.Close()
        return None
    px = h.ProjectionX()
    all_, acc = px.GetBinContent(1), px.GetBinContent(6)
    f.Close()
    return (acc / all_) if all_ > 0 else None


def cutflow(path):
    """Return the cutflow bin contents, or None if the file is not there."""
    if not os.path.exists(path):
        return None
    f = ROOT.TFile.Open(path)
    if not f or f.IsZombie():
        return None
    d = f.Get('CutBasedDM')
    h = d.Get(CUTFLOW) if d else None
    if not h:
        f.Close()
        return None
    px = h.ProjectionX()
    vals = [px.GetBinContent(i + 1) for i in range(px.GetNbinsX())]
    f.Close()
    return vals


def fmt_bkg(n):
    if n is None:
        return '--'
    if n < 1:
        return r'$<$1'
    return '{:,.0f}'.format(n)


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else 'analysis'

    bkg = {}
    cov_note = []
    for label, stem, samp_eot, tgt_eot in BKGS:
        vals = cutflow(os.path.join(d, stem + '_histos.root'))
        scale = None
        if vals and samp_eot:
            scale = tgt_eot / samp_eot
            sub = stem.replace('signal_v15_8gev_', 'signal_v15_8gev/')
            cov, ni, no = coverage(sub)
            if cov:
                scale *= cov
                cov_note.append('%% %-14s reco %d/%d inputs, coverage x%.4f'
                                % (label, no, ni, cov))
        bkg[label] = (vals, scale)

    sig = {}
    for label, stem in SIGS:
        sig[label] = cutflow(os.path.join(d, stem + '_histos.root'))

    out = []
    # Acceptance row: backgrounds are counted regardless of acceptance, signal
    # efficiency is quoted within it
    acc_cells = ['100.0\\%'] * len(BKGS)
    for label, stem in SIGS:
        a = acceptance_frac(os.path.join(d, stem + '_histos.root'))
        acc_cells.append('{:.1f}\\%'.format(100.0 * a) if a else '--')
    out.append('%-22s & %s \\\\ \\hline' % ('Acceptance', '\n& '.join(acc_cells)))

    for idx, row in ROWS:
        cells = []
        for label, _, _, _ in BKGS:
            vals, scale = bkg[label]
            cells.append(fmt_bkg(vals[idx] * scale) if (vals and scale) else '--')
        for label, _ in SIGS:
            v = sig[label]
            if not v or v[3] <= 0:
                cells.append('--')
            else:
                cells.append('{:.1f}\\%'.format(100.0 * v[idx] / v[3]))
        out.append('%-22s & %s \\\\ \\hline' % (row, '\n& '.join(cells)))

    print('\n'.join(out))
    print()
    print('\n'.join(cov_note))
    print('%% raw (unscaled) cutflow bin contents, for checking')
    for label, stem, samp_eot, tgt_eot in BKGS:
        vals, scale = bkg[label]
        if vals:
            print('%% %-14s scale=%-6s %s' % (
                label, ('%.4g' % scale) if scale else 'n/a',
                ' '.join('%d:%.0f' % (i, vals[i]) for i, _ in ROWS)))
        else:
            print('%% %-14s MISSING %s' % (label, stem))
    for label, stem in SIGS:
        v = sig[label]
        print('%% %-14s %s' % (label,
              ' '.join('%d:%.0f' % (i, v[i]) for i, _ in ROWS) if v else 'MISSING ' + stem))


if __name__ == '__main__':
    main()
