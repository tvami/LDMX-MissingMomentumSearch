#!/usr/bin/env python3
"""Are the surviving background events ones with no ECal hits?

Every cut-and-count threshold is an upper bound (E_sum < 3500, N_hits < 70, and
so on), and the loose ParticleNet preselection is too, so an event with zero
ECal readout hits passes all of them for free. If such events exist in the
preselected sample in roughly the number that survives, that is the explanation
for the surviving yield.

Projects NReadoutHits and SummedDet at the Preselection stage and counts the
zero-hit population, scaled to 1.5e14 EoT.
"""
import sys

import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kFatal

ANA = sys.argv[1] if len(sys.argv) > 1 else 'analysis_pnetv11'
STAGE = 3          # "Preselection"
SAMPLES = [('ecal_pn_v15_8gev', 1.5e14 / 1.5e14 * 6172.0 / 5921.0),
           ('ecal_conversion_v15_8gev', 1.5e14 / 1.0e15 * 991.0 / 933.0),
           ('target_pn_v15_8gev', 0.15),
           ('target_conversion_v15_8gev', 0.15),
           ('signal_v15_8gev_0.001', 1.0),
           ('signal_v15_8gev_1.0', 1.0)]


def proj(stem, var):
    f = ROOT.TFile.Open('%s/%s_histos.root' % (ANA, stem))
    if not f or f.IsZombie():
        return None
    h2 = f.Get('CutBasedDM').Get(var)
    if not h2:
        f.Close()
        return None
    h = h2.ProjectionY('p_%s_%s' % (stem, var), STAGE + 1, STAGE + 1)
    h.SetDirectory(0)
    f.Close()
    return h


print('%-28s %14s %12s %10s %12s' %
      ('sample', 'at presel', 'N_hits=0', 'frac', 'scaled to EoT'))
for stem, scale in SAMPLES:
    h = proj(stem, 'NReadoutHits')
    if not h:
        print('%-28s  missing' % stem)
        continue
    tot = h.Integral(0, h.GetNbinsX() + 1)
    # bins are integer-centred from -0.5, so bin 1 is exactly N_hits = 0
    zero = h.GetBinContent(1)
    print('%-28s %14.0f %12.0f %9.5f%% %12.1f'
          % (stem, tot, zero, 100 * zero / tot if tot else 0, zero * scale))

print()
print('Lowest N_hits bins for ECal PN at preselection:')
h = proj('ecal_pn_v15_8gev', 'NReadoutHits')
for i in range(1, 11):
    print('  N_hits = %2d : %10.0f' % (i - 1, h.GetBinContent(i)))

print()
print('SummedDet in the lowest bins for ECal PN (0 to 100 MeV per bin):')
hs = proj('ecal_pn_v15_8gev', 'SummedDet')
for i in range(1, 6):
    print('  [%6.0f, %6.0f) MeV : %10.0f'
          % (hs.GetXaxis().GetBinLowEdge(i), hs.GetXaxis().GetBinUpEdge(i),
             hs.GetBinContent(i)))
