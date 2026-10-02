#!/usr/bin/env python3
"""ParticleNet v11 discriminator plots for the cut-and-count / PNet talk.

Two plots, both from the PNetDisc histogram, which is filled for every event
passing acceptance + trigger + the loose PNet preselection:

  pnet_disc.pdf      unit-area disc distributions, the four signal masses
                     against all four backgrounds
  pnet_workingpoint.pdf  ECal PN yield vs signal efficiency as the cut moves

Both are at the PNet step, BEFORE the HCal veto, because PNetDisc carries no
HCal information. The HCal veto after it removes a further ~4 orders of
magnitude of ECal PN, so these are separation plots, not final yields.

pnet_disc is drawn in the house style of compareWithArguementList2D.py
(ldmx_plot_style.py): square canvas, the four stamps, markers with error bars,
unit area to 3000, overflow folded in. The signal colors are the validated
CVD-safe set rather than the reference's kRed/kGreen cycle; the backgrounds are
a neutral family, ECal PN as a shaded band and the rest as points of varying
shape and lightness. See ldmx_plot_style for why.

pnet_workingpoint is NOT yet restyled: per section 4.2 of the restyle plan its
content changes with the zero-ECal-hit re-run, so look and message are redone
together.

Usage: plot_pnet_disc.py [analysis_dir] [out_dir] [bkg_mode]
       bkg_mode: shade (default) | hatch | point
"""
import os
import sys

import ROOT

import ldmx_plot_style as st

st.init()

ANA = sys.argv[1] if len(sys.argv) > 1 else 'analysis_pnetv11'
OUT = sys.argv[2] if len(sys.argv) > 2 else \
    '/sdf/group/ldmx/users/tamasvami/ldmx-analysis/presentation_cnc_pnet_v15/plots_cnc_pnet'
BKG_MODE = sys.argv[3] if len(sys.argv) > 3 else st.BKG_MODE
CUT = 0.5664
# tree whose PNetDisc is filled after the ECal hit requirement, for the dashed
# curves of the working-point plot; "--hit-tree DIR", a flag since denv drops env vars
HIT_TREE = 'analysis_aligned'
if '--hit-tree' in sys.argv:
    _i = sys.argv.index('--hit-tree')
    HIT_TREE = sys.argv[_i + 1]
    del sys.argv[_i:_i + 2]
    # positional args were read above, so re-read them without the flag
    ANA = sys.argv[1] if len(sys.argv) > 1 else ANA
    OUT = sys.argv[2] if len(sys.argv) > 2 else OUT
    BKG_MODE = sys.argv[3] if len(sys.argv) > 3 else BKG_MODE
# the floor is ~1.2e4, the hit-required curves reach ~12: span both, with room
# above for the legend
WP_YMIN, WP_YMAX = 3.0, 3e9
# house unit-area range, the same one style_axes applies
YMIN, YMAX = 1e-6, 3000.0
# ECal PN: 1.5e14 EoT sample, coverage 6172/5921
BKG_SCALE = 1.5e14 / 1.5e14 * (6172.0 / 5921.0)

SIGS = [('signal_v15_8gev_0.001', '1 MeV',    st.COLORS[0]),
        ('signal_v15_8gev_0.01',  '10 MeV',   st.COLORS[1]),
        ('signal_v15_8gev_0.1',   '100 MeV',  st.COLORS[2]),
        ('signal_v15_8gev_1.0',   '1000 MeV', st.COLORS[3])]
# the dominant background, which the yield numbers below are quoted for
BKG = ('ecal_pn_v15_8gev', 'ECal PN', st.BKG_COLOR)

XTITLE = 'ParticleNet v11 discriminator'


def get(stem):
    f = ROOT.TFile.Open('%s/%s_histos.root' % (ANA, stem))
    if not f or f.IsZombie():
        raise SystemExit('cannot open %s' % stem)
    h = f.Get('CutBasedDM').Get('PNetDisc')
    h = h.Clone(stem)
    h.SetDirectory(0)
    f.Close()
    return h


def eff_above(h, cut):
    """Fraction of loose-preselected events with disc above cut.

    Denominator is GetEntries(), which includes the underflow where the disc is
    -99 because ParticleNet did not run (no recoil track, or too many hits).
    Those events fail the cut, so they belong in the denominator.
    """
    n = h.GetEntries()
    if not n:
        return 0.0
    lo = h.GetXaxis().FindBin(cut + 1e-9)
    return h.Integral(lo, h.GetNbinsX() + 1) / n


def plot_disc():
    c = st.canvas('cPNetDisc')
    keep = []

    # backgrounds first, so the colored signal markers end up on top
    series = ([(stem, fc, lc, fill, mk) for stem, fc, lc, fill, mk in st.bkgs(BKG_MODE)] +
              [(stem, col, col, None, 20) for stem, col in st.SIGS])
    first = True
    for stem, fc, lc, fill, mk in series:
        h = get(stem)
        st.add_overflow(h)
        st.normalize(h)
        if fill is None:                       # signal
            st.style_signal(h, fc, marker=mk)
            kind = 'point'
        else:                                  # background
            st.style_bkg(h, fc, lc, fill, marker=mk)
            kind = 'point' if not fill else 'fill'
        if first:
            st.style_axes(h, XTITLE)
        h.Draw(st.draw_opt(first, kind))
        first = False
        keep.append((h, stem, kind))

    hb = keep[0][0]
    labels = [st.label_for(s) for _, s, _ in keep]
    leg = st.make_legend(max(len(l) for l in labels), y0=st.LEGEND_Y0,
                         x0=st.LEGEND_X0)
    for h, stem, kind in keep:
        leg.AddEntry(h, st.label_for(stem), st.legend_opt(kind))
    leg.Draw('SAME')

    # no sample stamp: the slide says which sample and where in the flow this is,
    # and dropping it lets the bottom margin come in
    texts = st.stamps()
    for t in texts:
        t.Draw('SAME')

    # both markers stop under the legend rather than running through it
    ytop = st.line_top(YMIN, YMAX)

    # the shipped working point, a dashed line and nothing else: the line says
    # where the threshold is without a word on it
    cut_line = st.dashed_line()
    cut_line.DrawLine(CUT, YMIN, CUT, ytop)

    # house overflow marker
    ofl = st.dashed_line()
    ofl.SetLineStyle(ROOT.kDotted)
    ofl.DrawLine(st.overflow_x(hb), YMIN, st.overflow_x(hb), ytop)

    for ext in ('pdf', 'png'):
        c.SaveAs('%s/pnet_disc.%s' % (OUT, ext))


def plot_workingpoint():
    """ECal PN events surviving the PNet cut vs signal efficiency, cut scanned.

    Two curve sets, before the HCal veto:
      solid   as reconstructed (ANA), which flattens at ~1.2e4 events: the
              events with no ECal readout hits, which sit at disc = 1 exactly
      dashed  with at least one ECal hit required (HIT_TREE, whose PNetDisc is
              filled after the hit requirement), where the floor is gone
    House style: square canvas, stamps, legend from ldmx_plot_style.
    """
    def curves(tree):
        f = ROOT.TFile.Open('%s/%s_histos.root' % (tree, BKG[0]))
        hb = f.Get('CutBasedDM').Get('PNetDisc').Clone('wp_bkg_' + tree)
        hb.SetDirectory(0)
        f.Close()
        sig = {}
        for stem, lab, _ in SIGS:
            f = ROOT.TFile.Open('%s/%s_histos.root' % (tree, stem))
            h = f.Get('CutBasedDM').Get('PNetDisc').Clone('wp_%s_%s' % (stem, tree))
            h.SetDirectory(0)
            f.Close()
            sig[lab] = h
        return hb, sig

    c = st.canvas('cPNetWP')
    frame = ROOT.TH1F('frameWP', '', 100, 0.0, 100.0)
    st.style_axes(frame, 'signal efficiency after loose preselection [%]',
                  ytitle='ECal PN events, before the HCal veto',
                  ymin=WP_YMIN, ymax=WP_YMAX)
    frame.Draw('AXIS')

    keep = [frame]
    legend_lines = []
    for tree, lstyle in ((ANA, 1), (HIT_TREE, ROOT.kDashed)):
        hb, sig = curves(tree)
        for stem, lab, col in SIGS:
            g = ROOT.TGraph()
            h = sig[lab]
            for i in range(1, hb.GetNbinsX() + 1):
                cut = hb.GetXaxis().GetBinLowEdge(i)
                es = eff_above(h, cut)
                nb = eff_above(hb, cut) * hb.GetEntries() * BKG_SCALE
                if es > 0 and nb > 0:
                    g.SetPoint(g.GetN(), 100 * es, nb)
            g.SetLineColor(ROOT.TColor.GetColor(col))
            g.SetLineWidth(3)
            g.SetLineStyle(lstyle)
            g.Draw('L SAME')
            keep.append(g)
            if lstyle == 1:
                legend_lines.append((g, st.label_for(stem)))
        # the shipped working point on this curve set
        mk = ROOT.TGraph()
        for stem, lab, col in SIGS:
            mk.SetPoint(mk.GetN(), 100 * eff_above(sig[lab], CUT),
                        eff_above(hb, CUT) * hb.GetEntries() * BKG_SCALE)
        mk.SetMarkerStyle(20 if lstyle == 1 else 24)
        mk.SetMarkerSize(1.4)
        mk.SetMarkerColor(ROOT.kBlack)
        mk.Draw('P SAME')
        keep.append(mk)

    # line-style key, in neutral grey so it does not read as another mass
    key_solid = ROOT.TGraph()
    key_solid.SetLineColor(ROOT.TColor.GetColor(st.BKG_COLOR))
    key_solid.SetLineWidth(3)
    key_dash = key_solid.Clone()
    key_dash.SetLineStyle(ROOT.kDashed)
    key_mk = ROOT.TGraph()
    key_mk.SetMarkerStyle(20)
    key_mk.SetMarkerSize(1.4)
    keep += [key_solid, key_dash, key_mk]

    leg = st.make_legend(20, y0=st.LEGEND_Y0, x0=st.LEGEND_X0)
    for g, lab in legend_lines:
        leg.AddEntry(g, lab, 'L')
    leg.AddEntry(key_solid, 'as reconstructed', 'L')
    leg.AddEntry(key_dash, '#geq 1 ECal hit', 'L')
    leg.AddEntry(key_mk, 'cut 0.5664', 'P')
    leg.Draw('SAME')

    texts = st.stamps()
    for t in texts:
        t.Draw('SAME')

    c.RedrawAxis()
    for ext in ('pdf', 'png'):
        c.SaveAs('%s/pnet_workingpoint.%s' % (OUT, ext))


def main():
    os.makedirs(OUT, exist_ok=True)
    plot_disc()
    plot_workingpoint()

    # numbers the talk quotes, so they are never typed by hand
    # The saturation bin is the one holding disc = 1.0, NOT GetNbinsX(): the axis
    # runs to 1.05, so the last bin is [1.04, 1.05) and can never be filled.
    def sat(h):
        b = h.GetXaxis().FindBin(1.0)
        return 100.0 * h.Integral(b, h.GetNbinsX() + 1) / h.GetEntries()

    hb = get(BKG[0])
    print('ECal PN  loosePresel entries: %.0f' % hb.GetEntries())
    print('  above cut: %.4f%%  (bin-quantised, the cutflow is exact)'
          % (100 * eff_above(hb, CUT)))
    print('  in the disc >= 1.0 bin: %.3f%%' % sat(hb))
    for stem, lab, _ in SIGS:
        h = get(stem)
        print('%-9s above cut %.2f%%   disc >= 1.0 pile-up %.2f%%'
              % (lab, 100 * eff_above(h, CUT), sat(h)))


if __name__ == '__main__':
    main()
