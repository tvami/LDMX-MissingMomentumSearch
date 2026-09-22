"""Overlay the cutflows of two analysis outputs on the same canvas.

Usage:
  python3 overlayCutflow.py <fileA> <labelA> <fileB> <labelB> [outdir]

e.g.
  python3 overlayCutflow.py analysis/ecal_pn_v15_8gev_all_histo.root segmip \
                            analysis_helena/ecal_pn_v15_8gev_all_histo.root helena \
                            CompareBDTs

For every CutFlow TH2 present in both files it writes two plots:
  <outdir>/Overlay_<name>.png      absolute yields, log y
  <outdir>/OverlayNorm_<name>.png  efficiency, each normalised to its own bin 1

The cutflow TH1 is taken as ProjectionX(), matching compareCutflow.py, so the
curves here are the same numbers as the existing CutFlow_*.png plots.
"""

import os
import sys

import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kWarning

file_a, label_a, file_b, label_b = sys.argv[1:5]
outdir = sys.argv[5] if len(sys.argv) > 5 else "CompareBDTs"

f_a = ROOT.TFile.Open(file_a)
f_b = ROOT.TFile.Open(file_b)
if not f_a or not f_b:
    raise SystemExit("could not open both input files")

if not os.path.exists(outdir):
    os.makedirs(outdir)

COL_A, COL_B = ROOT.kBlue + 1, ROOT.kRed + 1


def cutflow_names(f):
    """Every <dir>/<hist> in f whose histogram is a CutFlow TH2."""
    out = []
    for key in f.GetListOfKeys():
        d = f.GetDirectory(key.GetName())
        if not d:
            continue
        for k2 in d.GetListOfKeys():
            if "CutFlow" not in k2.GetName():
                continue
            obj = d.Get(k2.GetName())
            if obj and obj.InheritsFrom("TH2"):
                out.append(key.GetName() + "/" + k2.GetName())
    return out


def styled_projection(f, path, color, marker):
    h2 = f.Get(path)
    if not h2:
        return None
    h = h2.ProjectionX(path.replace("/", "_") + "_px_%d" % color)
    h.SetDirectory(0)
    h.SetStats(0)
    h.SetLineColor(color)
    h.SetLineWidth(2)
    h.SetMarkerColor(color)
    h.SetMarkerStyle(marker)
    h.SetMarkerSize(1.2)
    return h


def ldmx_labels():
    """The LDMX / Simulation / EOT tags used by compareCutflow.py."""
    out = []
    t = ROOT.TLatex(0.15, 0.92, "LDMX")
    t.SetNDC(); t.SetTextFont(61); t.SetTextSize(0.0675); t.SetLineWidth(2)
    out.append(t)
    t = ROOT.TLatex(0.33, 0.92, "Simulation")
    t.SetNDC(); t.SetTextFont(52); t.SetTextSize(0.0485); t.SetLineWidth(2)
    out.append(t)
    t = ROOT.TLatex(0.57, 0.92, "1.5#times10^{14} EOT (8 GeV)")
    t.SetNDC(); t.SetTextFont(42); t.SetTextSize(0.040); t.SetLineWidth(2)
    out.append(t)
    return out


ROOT.gStyle.SetPadRightMargin(0.09)
ROOT.gStyle.SetPadTopMargin(0.10)
ROOT.gStyle.SetPadBottomMargin(0.20)
ROOT.gStyle.SetPadLeftMargin(0.15)

names_a = cutflow_names(f_a)
names_b = set(cutflow_names(f_b))
shared = [n for n in names_a if n in names_b]
print("overlaying %d cutflow histograms" % len(shared))

for path in shared:
    short = path.split("/")[-1]

    for norm in (False, True):
        h_a = styled_projection(f_a, path, COL_A, 20)
        h_b = styled_projection(f_b, path, COL_B, 21)
        if not h_a or not h_b:
            continue

        if norm:
            for h in (h_a, h_b):
                if h.GetBinContent(1) > 0:
                    h.Scale(1.0 / h.GetBinContent(1))

        cname = "c_%s_%s" % (short, "norm" if norm else "abs")
        canvas = ROOT.TCanvas(cname, cname, 800, 800)

        # Drop the trailing unused bins - the cutflow TH2 is allocated with
        # more bins than there are cuts, and they stretch the axis flat.
        last = 1
        for i in range(1, h_a.GetNbinsX() + 1):
            if h_a.GetBinContent(i) > 0 or h_b.GetBinContent(i) > 0:
                last = i
        h_a.GetXaxis().SetRange(1, last)

        # A single surviving event must sit above the axis, not on it, so the
        # floor goes below the smallest non-zero entry rather than at 1.
        vals = [h.GetBinContent(i)
                for h in (h_a, h_b)
                for i in range(1, last + 1)
                if h.GetBinContent(i) > 0]
        lo = min(vals) / 5.0 if vals else (1e-9 if norm else 0.5)
        hi = max(h_a.GetMaximum(), h_b.GetMaximum())
        canvas.SetLogy()

        h_a.LabelsOption("v")
        h_a.GetYaxis().SetTitle("Efficiency" if norm else "Events / bin")
        h_a.GetYaxis().SetRangeUser(lo, hi * 50)
        h_a.Draw("HISTO P")
        h_b.Draw("HISTO P SAME")

        legend = ROOT.TLegend(0.62, 0.72, 0.90, 0.86)
        legend.SetLineColor(1)
        legend.SetLineStyle(1)
        legend.SetLineWidth(1)
        legend.SetFillColor(0)
        legend.SetFillStyle(0)
        legend.AddEntry(h_a, label_a, "LP")
        legend.AddEntry(h_b, label_b, "LP")
        legend.Draw("SAME")

        tags = ldmx_labels()
        for t in tags:
            t.Draw("SAME")

        prefix = "OverlayNorm_" if norm else "Overlay_"
        canvas.SaveAs("%s/%s%s.png" % (outdir, prefix, short))

print("wrote plots to %s/" % outdir)
