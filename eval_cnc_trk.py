#!/usr/bin/env python3
"""Cut and count at the v14 and Punzi-optimized thresholds, with and without
the tracker veto, from ntuple_cnc_trk/ (CnCNtuple with the trackerVeto branch).

Three closure rows must reproduce numbers already in the talk before the new
row means anything:

  A  v14, no tracker veto, full sample   CnCCutFlow with the hit requirement: 10
  B  v14, tracker veto,    full sample   CnCAlignedCutFlow: 9
  C  opt, no tracker veto, test half     Punzi test half: 6.3
  D  opt, tracker veto,    test half     new
  E  opt, tracker veto,    full sample   new, biased low (tuned on half of it)

All rows require trigger, acceptance and at least one ECal readout hit. Test
half is odd eventNumber; its yields are doubled to the full sample. Signal
efficiency is trig_eff x N(pass) / N(acceptance), in the same half.

Usage: eval_cnc_trk.py [ntuple_dir]
"""
import glob
import sys

import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kFatal

NT = sys.argv[1] if len(sys.argv) > 1 else 'ntuple_cnc_trk'
sys.stderr.write('reading %s/\n' % NT)

TGT = 1.5e14
PRES = '/sdf/data/ldmx/private_production/mc26/pres_skim/'
RECO = '/sdf/data/ldmx/private_production/mc26/reco_v492/'
BKGS = [('ecal_pn_v15_8gev', 1.5e14), ('ecal_conversion_v15_8gev', 1.0e15),
        ('target_pn_v15_8gev', 1.0e15), ('target_conversion_v15_8gev', 1.0e15)]
SIGS = [('signal_v15_8gev/0.001', 0.8641), ('signal_v15_8gev/0.01', 0.8578),
        ('signal_v15_8gev/0.1', 0.8672), ('signal_v15_8gev/1.0', 0.8648)]

V14 = [('summedDet', 3500.), ('summedTightIso', 800.), ('ecalBackEnergy', 250.),
       ('nReadoutHits', 70.), ('showerRMS', 110.), ('maxCellDep', 300.),
       ('stdLayerHit', 5.), ('nStraight', 3.), ('hcalMaxPE', 8.)]
# scan_out/cnc_punzi_results.json, "nhits>=1 a=3", thr
OPT = [('summedDet', 5101.6949152542375), ('summedTightIso', 1600.0),
       ('ecalBackEnergy', 500.0), ('nReadoutHits', 57.0), ('showerRMS', 220.0),
       ('maxCellDep', 600.0), ('stdLayerHit', 10.0), ('nStraight', 2.0),
       ('hcalMaxPE', 8.0)]

ROWS = [('A', 'v14, no tracker veto, full', V14, False, False),
        ('B', 'v14, tracker veto, full', V14, True, False),
        ('C', 'opt, no tracker veto, test', OPT, False, True),
        ('D', 'opt, tracker veto, test', OPT, True, True),
        ('E', 'opt, tracker veto, full', OPT, True, False)]


def coverage(sub):
    ni = len(glob.glob(PRES + sub + '/*.root'))
    no = len(glob.glob(RECO + sub + '/*_reco.root'))
    return float(ni) / no if (ni and no) else 1.0


WEIGHT = {s: TGT / e * coverage(s) for s, e in BKGS}


def chain(sample):
    c = ROOT.TChain('CnCNtuple/cnc')
    n = c.Add('%s/%s/*_histo.root' % (NT, sample))
    if not n:
        raise SystemExit('no files for %s' % sample)
    return c


def selection(thr, trk, test):
    parts = ['trigger', 'acceptance', 'nReadoutHits >= 1']
    parts += ['%s < %r' % (k, v) for k, v in thr]
    if trk:
        parts.append('trackerVeto')
    if test:
        parts.append('eventNumber % 2 == 1')
    return ' && '.join(parts)


def main():
    chains = {s: chain(s) for s, _ in BKGS + [(x[0], 0) for x in SIGS]}
    for tag, desc, thr, trk, test in ROWS:
        sel = selection(thr, trk, test)
        half = 2.0 if test else 1.0
        raw = {s: chains[s].GetEntries(sel) for s, _ in BKGS}
        epn = raw['ecal_pn_v15_8gev'] * WEIGHT['ecal_pn_v15_8gev'] * half
        tot = sum(raw[s] * WEIGHT[s] * half for s, _ in BKGS)
        den_sel = 'acceptance' + (' && eventNumber % 2 == 1' if test else '')
        effs = []
        for s, trig in SIGS:
            num = chains[s].GetEntries(sel)
            den = chains[s].GetEntries(den_sel)
            effs.append(100.0 * trig * num / den if den else 0.0)
        print('%s  %-30s ECal PN raw %3d -> %6.2f   all bkg %6.2f   signal %s'
              % (tag, desc, raw['ecal_pn_v15_8gev'], epn, tot,
                 ' / '.join('%.1f%%' % e for e in effs)))
        sys.stdout.flush()


if __name__ == '__main__':
    main()
