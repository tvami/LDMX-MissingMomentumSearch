"""House plot style for the missing-momentum analysis.

Lifted from compareWithArguementList2D.py, which produces CompareHistos_v492/
and the proceeding figures, so plots written with this module sit beside those
without looking foreign.

Two deliberate departures from the reference, both documented in
presentation_cnc_pnet_v15/PLOT_RESTYLE_PLAN.md:

  colors   the reference cycles kRed, kGreen, kBlue, kYellow, ... which is not
           colorblind-safe and puts kYellow on white. COLORS below is the
           validated set, assigned in fixed order and never cycled.
  bkg mode the backgrounds are shaded rather than drawn as points, so the
           signal markers read on top of them rather than competing with them.
           BKG_MODE picks how the shading is done.
"""
import math

import ROOT

# validated CVD-safe categorical series, fixed order, never cycled
COLORS = ['#0072B2', '#D55E00', '#009E73', '#9467BD']
# the background is a reference distribution, not another category
BKG_COLOR = '#555555'

# The four signal masses carry the validated hues, as everywhere else in the
# talk. That leaves no hue for the backgrounds, so they are a neutral family
# instead. Black is not in that family: black markers mean real data.
#
# All four are shaded. Four filled areas on a seven-decade log plot do overlap,
# so what tells them apart is the outline, drawn at full opacity over a
# see-through fill. Two ways of doing the fill, BKG_MODE picks one:
#
#   shade    a grey ramp, every fill translucent
#   hatch    one solid fill for the background that carries the yield, hatched
#            fills at three angles for the rest
#   point    no fill at all, the reference's markers, for comparison
#
# A fill and a stroke do not need the same contrast: a large area reads at a
# lightness where a thin line would disappear, which is why the fills can be
# light colors that would fail as marker colors. These are Paul Tol's light
# qualitative scheme, which is meant for exactly this, shaded areas that stay
# distinguishable under colorblindness. Each is paired with a darker stroke of
# its own hue, since with four areas overlapping the outline is what says which
# is which.
#
# No orange among them on purpose: it would sit next to the vermillion the
# 10 MeV signal uses.
#
# stem, fill, outline, fill style, marker
BKGS_COLOR = [
    ('ecal_pn_v15_8gev',           '#77AADD', '#2A6496', 1001, 20),
    ('target_pn_v15_8gev',         '#EEDD88', '#9A7D1A', 1001, 21),
    ('ecal_conversion_v15_8gev',   '#FFAABB', '#B3516A', 1001, 22),
    ('target_conversion_v15_8gev', '#44BB99', '#1F7A5E', 1001, 23),
]
# the dominant background stays neutral, the rest take colour: ECal PN is the
# one that carries the yield, so it reads as the reference the others sit against
BKGS_MIXED = [
    ('ecal_pn_v15_8gev',           '#555555', '#333333', 1001, 20),
    ('target_pn_v15_8gev',         '#77AADD', '#2A6496', 1001, 21),
    ('ecal_conversion_v15_8gev',   '#EEDD88', '#9A7D1A', 1001, 22),
    ('target_conversion_v15_8gev', '#FFAABB', '#B3516A', 1001, 23),
]
BKGS_TONE = [
    ('ecal_pn_v15_8gev',           '#333333', '#333333', 1001, 20),
    ('target_pn_v15_8gev',         '#5F5F5F', '#5F5F5F', 1001, 21),
    ('ecal_conversion_v15_8gev',   '#8A8A8A', '#8A8A8A', 1001, 22),
    ('target_conversion_v15_8gev', '#B5B5B5', '#B5B5B5', 1001, 23),
]
BKGS_PATTERN = [
    ('ecal_pn_v15_8gev',           '#555555', '#555555', 1001, 20),
    ('target_pn_v15_8gev',         '#333333', '#333333', 3004, 21),
    ('ecal_conversion_v15_8gev',   '#555555', '#555555', 3005, 22),
    ('target_conversion_v15_8gev', '#777777', '#777777', 3007, 23),
]

_BKG_MODES = {
    'color': BKGS_COLOR,
    'mixed': BKGS_MIXED,
    'shade': BKGS_TONE,
    'hatch': BKGS_PATTERN,
}


def bkgs(mode=None):
    """The background series for a background mode."""
    mode = mode or BKG_MODE
    if mode == 'point':
        return [(s, f, l, 0, m) for s, f, l, _, m in BKGS_COLOR]
    return _BKG_MODES.get(mode, BKGS_COLOR)

# eight entries of "m_{A'} = 1000 MeV" length do not fit the columns the
# reference's x0 steps give, which are sized for file names
LEGEND_X0 = 0.40
# bottom of the legend box; vertical markers stop just under it
LEGEND_Y0 = 0.63

# stem, color; marker 20 throughout, as the reference does
SIGS = [
    ('signal_v15_8gev_0.001', COLORS[0]),
    ('signal_v15_8gev_0.01',  COLORS[1]),
    ('signal_v15_8gev_0.1',   COLORS[2]),
    ('signal_v15_8gev_1.0',   COLORS[3]),
]

EOT_TEXT = '1.5#times10^{14} EoT (8 GeV)'

# how the backgrounds are drawn, see bkgs() below
BKG_MODE = 'mixed'
# four fills land on top of each other, so they have to be see-through
SHADE_ALPHA = 0.30


# The reference's margins are right 0.15 and bottom 0.20: the first leaves room
# for the colour palette of a 2D plot, the second for the sample stamp along the
# bottom edge. Neither applies to these overlays, so both come in and the frame
# gets the space instead.
MARGINS = dict(left=0.15, right=0.05, top=0.10, bottom=0.14)


def _set_margins(pad):
    pad.SetLeftMargin(MARGINS['left'])
    pad.SetRightMargin(MARGINS['right'])
    pad.SetTopMargin(MARGINS['top'])
    pad.SetBottomMargin(MARGINS['bottom'])


def init():
    """Batch mode and the house pad margins."""
    ROOT.gROOT.SetBatch(True)
    ROOT.gErrorIgnoreLevel = ROOT.kWarning
    ROOT.gStyle.SetOptStat(0)
    ROOT.gStyle.SetPadTickX(1)
    ROOT.gStyle.SetPadTickY(1)
    ROOT.gStyle.SetPadLeftMargin(MARGINS['left'])
    ROOT.gStyle.SetPadRightMargin(MARGINS['right'])
    ROOT.gStyle.SetPadTopMargin(MARGINS['top'])
    ROOT.gStyle.SetPadBottomMargin(MARGINS['bottom'])


def canvas(name, logy=True, w=800, h=800):
    """Square canvas with the house margins."""
    c = ROOT.TCanvas(name, name, w, h)
    _set_margins(c)
    if logy:
        c.SetLogy()
    return c


def stamps(sample=None, eot_text=EOT_TEXT, scale=1.0):
    """The four house text stamps, positioned. The caller must keep the list
    alive: ROOT deletes unreferenced objects.

    scale multiplies the text sizes, for canvases that are not 800x800.
    """
    out = []

    tex2 = ROOT.TLatex(0.15, 0.92, 'LDMX')
    tex2.SetTextFont(61)
    tex2.SetTextSize(0.06 * scale)
    out.append(tex2)

    tex3 = ROOT.TLatex(0.31, 0.92, 'Simulation')
    tex3.SetTextFont(52)
    tex3.SetTextSize(0.04 * scale)
    out.append(tex3)

    tex4 = ROOT.TLatex(0.62, 0.92, eot_text)
    tex4.SetTextFont(52)
    tex4.SetTextSize(0.025 * scale)
    out.append(tex4)

    if sample is not None:
        # x backs off from the right edge by the length of the name
        tex5 = ROOT.TLatex((120 - (len(sample) + 4)) / 120.0, 0.015,
                           'Sample: ' + sample)
        tex5.SetTextFont(52)
        tex5.SetTextSize(0.017 * scale)
        out.append(tex5)

    for t in out:
        t.SetNDC()
        t.SetLineWidth(2)
    return out


def make_legend(nlongest, ncol=2, y0=0.70, x0=None):
    """Legend box, x0 stepping with the longest entry as the reference does.

    The reference's steps are tuned to file names, which are far longer than
    these display labels, so x0 can be given outright where the steps leave the
    columns too narrow.
    """
    if x0 is None:
        x0 = 0.6
        if nlongest >= 25:
            x0 = 0.5
        if nlongest >= 40:
            x0 = 0.3
        if nlongest >= 55:
            x0 = 0.2
    leg = ROOT.TLegend(x0 - 0.10, y0, 0.85, 0.89, '', 'brNDC')
    leg.SetTextFont(42)
    leg.SetTextSize(0.03)
    leg.SetBorderSize(0)
    leg.SetLineColor(1)
    leg.SetLineStyle(1)
    leg.SetLineWidth(1)
    leg.SetFillColor(0)
    leg.SetFillStyle(0)
    leg.SetNColumns(ncol)
    return leg


def add_overflow(h, xmax=None):
    """Fold the overflow into the last visible bin.

    With xmax given, everything above xmax is folded instead, so a panel that
    shows only part of its axis still shows all of its events. Returns the bin
    the content was folded into.
    """
    n = h.GetNbinsX()
    last = n if xmax is None else h.GetXaxis().FindBin(xmax - 1e-9)
    last = max(1, min(last, n))
    tot = h.GetBinContent(last)
    err2 = h.GetBinError(last) ** 2
    for b in range(last + 1, n + 2):
        tot += h.GetBinContent(b)
        err2 += h.GetBinError(b) ** 2
        h.SetBinContent(b, 0)
        h.SetBinError(b, 0)
    h.SetBinContent(last, tot)
    h.SetBinError(last, err2 ** 0.5)
    return last


def overflow_x(h, xmax=None):
    """x of the dashed overflow marker, half a bin before the folded bin."""
    n = h.GetNbinsX()
    last = n if xmax is None else h.GetXaxis().FindBin(xmax - 1e-9)
    last = max(1, min(last, n))
    ax = h.GetXaxis()
    return ax.GetBinCenter(last) - ax.GetBinWidth(last) / 2.0


def dashed_line():
    ln = ROOT.TLine()
    ln.SetLineWidth(2)
    ln.SetLineStyle(ROOT.kDashed)
    return ln


def y_at_ndc(ndc, ymin, ymax):
    """The axis value at a height given in pad NDC, for a log y pad."""
    frac = ((ndc - MARGINS['bottom']) /
            (1.0 - MARGINS['bottom'] - MARGINS['top']))
    lo, hi = math.log10(ymin), math.log10(ymax)
    return 10.0 ** (lo + frac * (hi - lo))


def line_top(ymin, ymax, below=None):
    """Where a vertical marker should stop: just under the legend, so it does
    not run through it."""
    return y_at_ndc((LEGEND_Y0 if below is None else below) - 0.02,
                    ymin, ymax)


def normalize(h):
    """Unit area over the visible axis, the reference's convention."""
    integral = h.Integral(1, h.GetNbinsX() + 1)
    if integral > 0:
        h.Scale(1.0 / integral)
    return h


def style_signal(h, color, marker_size=None, marker=20):
    """Points with error bars, drawn with draw_opt(..., 'point')."""
    col = ROOT.TColor.GetColor(color)
    h.SetStats(0)
    h.SetTitle('')
    h.SetMarkerStyle(marker)
    h.SetMarkerColor(col)
    h.SetLineColor(col)
    if marker_size:
        h.SetMarkerSize(marker_size)
    return h


def style_bkg(h, color=BKG_COLOR, line=None, fill=1001, marker_size=None,
              marker=20):
    """A shaded background. fill is a ROOT fill style, or 0 for markers only.

    A solid fill is made translucent so the ones underneath still read; a
    hatch pattern is see-through already. Either way the outline is drawn at
    full opacity in its own darker colour, because the outline is what tells
    the four apart.
    """
    col = ROOT.TColor.GetColor(color)
    lcol = ROOT.TColor.GetColor(line) if line else col
    h.SetStats(0)
    h.SetTitle('')
    h.SetLineColor(lcol)
    h.SetMarkerColor(lcol)
    h.SetMarkerStyle(marker)
    if marker_size:
        h.SetMarkerSize(marker_size)
    if not fill:
        h.SetFillStyle(0)
    elif fill == 1001:
        h.SetFillColorAlpha(col, SHADE_ALPHA)
        h.SetFillStyle(1001)
        h.SetLineWidth(2)
    else:
        h.SetFillColor(col)
        h.SetFillStyle(fill)
        h.SetLineWidth(2)
    return h


def draw_opt(first, kind='point'):
    """Draw option for a series. Backgrounds are drawn first, so the signal
    markers land on top of the shaded band."""
    if kind == 'point':
        return 'PE' if first else 'SAMEPE'
    return 'HIST' if first else 'HISTSAME'


def legend_opt(kind='point'):
    return 'LP' if kind == 'point' else 'F'


def style_axes(h, xtitle, ytitle='Normalized events / bin',
               ymin=1e-6, ymax=3000.0, title_size=None, label_size=None):
    h.SetTitle('')
    h.GetXaxis().SetTitle(xtitle)
    h.GetYaxis().SetTitle(ytitle)
    h.GetYaxis().SetRangeUser(ymin, ymax)
    if title_size:
        h.GetXaxis().SetTitleSize(title_size)
        h.GetYaxis().SetTitleSize(title_size)
    if label_size:
        h.GetXaxis().SetLabelSize(label_size)
        h.GetYaxis().SetLabelSize(label_size)
    return h


# filename substring -> legend label, the same strings the reference uses
_LABELS = [
    ('signal_v15_8gev_0.001', "m_{A'} = 1 MeV"),
    ('signal_v15_8gev_0.01', "m_{A'} = 10 MeV"),
    ('signal_v15_8gev_0.1', "m_{A'} = 100 MeV"),
    ('signal_v15_8gev_1.0', "m_{A'} = 1000 MeV"),
    ('ecal_conv', 'ECal conv.'),
    ('target_conv', 'Target conv.'),
    ('target_pn', 'Target PN'),
    ('ecal_pn', 'ECal PN'),
    ('target_en', 'Target EN'),
]


def label_for(stem):
    """House legend label for a sample stem. Longest match wins, so
    signal_v15_8gev_0.01 does not read as 0.001."""
    best = None
    for key, lab in _LABELS:
        if key in stem and (best is None or len(key) > len(best[0])):
            best = (key, lab)
    return best[1] if best else stem
