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

    Pending the re-run: section 4.2 of the restyle plan replaces the saturation
    claim with the zero-ECal-hit explanation and adds a second curve set, so the
    restyle happens then.
    """
    hb = get(BKG[0])
    sig = {lab: get(stem) for stem, lab, _ in SIGS}

    c = ROOT.TCanvas('c2', '', 900, 650)
    c.SetLogy()
    c.SetLeftMargin(0.13)
    c.SetBottomMargin(0.13)
    c.SetRightMargin(0.05)
    c.SetTopMargin(0.08)

    graphs = []
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
        g.SetLineWidth(2)
        g.SetTitle('')
        graphs.append((g, lab))

    first = True
    for g, lab in graphs:
        if first:
            g.GetXaxis().SetTitle('signal efficiency after loose preselection [%]')
            g.GetYaxis().SetTitle('ECal PN events at 1.5#times10^{14} EoT')
            g.GetXaxis().SetTitleSize(0.045)
            g.GetYaxis().SetTitleSize(0.045)
            g.GetXaxis().SetLimits(0.0, 100.0)
            # the curves flatten at the zero-ECal-hit floor near 1.2e4; do not
            # leave three empty decades under it
            g.SetMinimum(5e3)
            g.SetMaximum(3e7)
            g.Draw('AL')
            first = False
        else:
            g.Draw('L SAME')

    # the shipped working point
    mk = ROOT.TGraph()
    for stem, lab, col in SIGS:
        mk.SetPoint(mk.GetN(), 100 * eff_above(sig[lab], CUT),
                    eff_above(hb, CUT) * hb.GetEntries() * BKG_SCALE)
    mk.SetMarkerStyle(20)
    mk.SetMarkerSize(1.3)
    mk.SetMarkerColor(ROOT.kBlack)
    mk.Draw('P SAME')

    leg = ROOT.TLegend(0.17, 0.66, 0.60, 0.89)
    leg.SetBorderSize(0)
    leg.SetFillStyle(0)
    leg.SetTextSize(0.032)
    for g, lab in graphs:
        leg.AddEntry(g, lab, 'l')
    leg.AddEntry(mk, 'shipped working point', 'p')
    leg.Draw()

    t = ROOT.TLatex()
    t.SetNDC()
    t.SetTextSize(0.033)
    t.DrawLatex(0.135, 0.935, 'LDMX v15, 8 GeV, before the HCal veto')
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
