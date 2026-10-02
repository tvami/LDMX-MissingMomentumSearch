#!/usr/bin/env python3
"""The nine cut-and-count variables, signal against background, one plot each.

Each variable is stored as a 2D histogram of cut stage against value, so the
distributions are projected at the stage labelled "Preselection" (bin 4 of the
standard flow): after trigger and preselection, before any cut-and-count cut has
been applied. That is the point at which the chain starts cutting, so it is where
the thresholds are worth looking at.

One square plot per variable, written as cnc_<Variable>.pdf, in the house style
of compareWithArguementList2D.py (ldmx_plot_style.py): markers with error bars,
unit area to 3000, log y, overflow folded in, the four stamps. The background is
a shaded band rather than a fifth set of markers: it is a reference
distribution, not another category. The talk arranges the nine with LaTeX.

All four backgrounds and all four signal masses are drawn. The threshold is a
dashed line and nothing else: a line at a threshold does not need a word on it.

Two things to know about the ranges:

  - several variables are shown over only part of their axis, so the tail is
    folded into the last bin SHOWN rather than the end of the axis, with a
    dotted marker where it went. Nothing drops off the right edge silently, but
    it does put a spike there.
  - axis text is a little larger than the house default, because these are
    assembled several to a slide and then shrunk.

Usage: plot_cnc_vars.py [analysis_dir] [out_dir] [bkg_mode] [stamps]
       bkg_mode: shade (default) | hatch | point
       stamps:   stamps (default) | nostamps, for grid assembly, where nine
                 copies of the stamps at panel scale are unreadable
"""
import os
import sys

import ROOT

import ldmx_plot_style as st

st.init()

# "--thresholds opt" draws the Punzi-optimized thresholds (a = 3, ECal hits >= 1,
# scan_out/cnc_punzi_results.json "nhits>=1 a=3") and writes cnc_<Var>Opt.*;
# the default is the v14 thresholds. A flag, not an env var: denv drops those.
THR_SET = 'v14'
if '--thresholds' in sys.argv:
    _i = sys.argv.index('--thresholds')
    THR_SET = sys.argv[_i + 1]
    del sys.argv[_i:_i + 2]
OPT_THR = {'SummedDet': 5101.6949152542375, 'SummedTightIso': 1600.0,
           'EcalBackEnergy': 500.0, 'NReadoutHits': 57.0, 'ShowerRMS': 220.0,
           'MaxCellDep': 600.0, 'StdLayerHit': 10.0, 'Straight': 2.0,
           'Hcal_MaxPE': 8.0}
# "none" draws the distributions with no threshold line at all, cnc_<Var>NoCut.*
SUFFIX = {'opt': 'Opt', 'none': 'NoCut'}.get(THR_SET, '')

ANA = sys.argv[1] if len(sys.argv) > 1 else 'analysis_pnetv11'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'plots_pnet'
BKG_MODE = sys.argv[3] if len(sys.argv) > 3 else st.BKG_MODE
STAMPS = (sys.argv[4] if len(sys.argv) > 4 else 'stamps') != 'nostamps'
STAGE_BIN = 4      # "Preselection" in the 20-bin standard flow

# name, cut value, x range to show, axis title
VARS = [
    ('SummedDet',      3500., (0, 10000), 'E_{sum} [MeV]'),
    ('SummedTightIso',  800., (0, 3000),  'E_{sum, tight iso} [MeV]'),
    ('EcalBackEnergy',  250., (0, 1500),  'E_{back} [MeV]'),
    ('NReadoutHits',     70., (0, 150),   'N_{hits}'),
    ('ShowerRMS',       110., (0, 250),   'shower RMS [mm]'),
    ('MaxCellDep',      300., (0, 800),   'E_{cell, max} [MeV]'),
    ('StdLayerHit',       5., (0, 20),    'RMS of hit layers'),
    ('Straight',          3., (0, 10),    'N_{straight tracks}'),
    ('Hcal_MaxPE',        8., (0, 40),    'HCal max PE'),
]

# four backgrounds then four signals, drawn in that order so the colored signal
# markers end up on top. See ldmx_plot_style for the colour scheme.
SERIES = ([(stem, fc, lc, fill, mk) for stem, fc, lc, fill, mk in st.bkgs(BKG_MODE)] +
          [(stem, col, col, None, 20) for stem, col in st.SIGS])

# house unit-area range
YMIN, YMAX = 1e-6, 3000.0
# a little above the house default: these get shrunk into a grid on the slide
TITLE_SIZE, LABEL_SIZE = 0.055, 0.045


def proj(stem, var):
    f = ROOT.TFile.Open('%s/%s_histos.root' % (ANA, stem))
    if not f or f.IsZombie():
        raise SystemExit('cannot open %s' % stem)
    h2 = f.Get('CutBasedDM').Get(var)
    h = h2.ProjectionY('%s_%s' % (stem, var), STAGE_BIN, STAGE_BIN)
    h.SetDirectory(0)
    f.Close()
    return h


def plot_var(var, cut, xr, title):
    c = st.canvas('c_' + var)
    keep = []

    first = True
    for stem, fc, lc, fill, mk in SERIES:
        h = proj(stem, var)
        # fold at the right edge of what is shown, not the end of the axis
        st.add_overflow(h, xr[1])
        st.normalize(h)
        # stop just inside xr[1] so the folded bin is the last one shown
        h.GetXaxis().SetRangeUser(xr[0], xr[1] - 1e-9)
        if fill is None:                       # signal
            st.style_signal(h, fc, marker=mk)
            kind = 'point'
        else:                                  # background
            st.style_bkg(h, fc, lc, fill, marker=mk)
            kind = 'point' if not fill else 'fill'
        if first:
            st.style_axes(h, title, ymin=YMIN, ymax=YMAX,
                          title_size=TITLE_SIZE, label_size=LABEL_SIZE)
        h.Draw(st.draw_opt(first, kind))
        first = False
        keep.append((h, stem, kind))

    labels = [st.label_for(s) for _, s, _ in keep]
    leg = st.make_legend(max(len(l) for l in labels), y0=st.LEGEND_Y0,
                         x0=st.LEGEND_X0)
    for h, stem, kind in keep:
        leg.AddEntry(h, st.label_for(stem), st.legend_opt(kind))
    leg.Draw('SAME')

    # both markers stop under the legend rather than running through it
    ytop = st.line_top(YMIN, YMAX)

    # the threshold, unlabelled; left out entirely for the bare distributions
    if THR_SET != 'none':
        thr = st.dashed_line()
        thr.DrawLine(cut, YMIN, cut, ytop)

    # where the tail was folded in
    ofx = st.overflow_x(keep[0][0], xr[1])
    ofl = st.dashed_line()
    ofl.SetLineStyle(ROOT.kDotted)
    ofl.DrawLine(ofx, YMIN, ofx, ytop)

    texts = []
    if STAMPS:
        texts = st.stamps()
        for t in texts:
            t.Draw('SAME')

    # no underscore in the file name: it is read in LaTeX text mode by
    # \includegraphics and would need escaping at every use
    for ext in ('pdf', 'png'):
        c.SaveAs('%s/cnc_%s%s.%s' % (OUT, var.replace('_', ''), SUFFIX, ext))


def main():
    os.makedirs(OUT, exist_ok=True)
    sys.stderr.write('thresholds: %s\n' % THR_SET)
    for var, cut, xr, title in VARS:
        if THR_SET == 'opt':
            cut = OPT_THR[var]
        plot_var(var, cut, xr, title)


if __name__ == '__main__':
    main()
