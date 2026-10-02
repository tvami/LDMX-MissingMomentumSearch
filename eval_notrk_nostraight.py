#!/usr/bin/env python3
"""The three selections with no tracker veto and no N_straight cut.

Common cuts: trigger, acceptance, at least one ECal readout hit, HCal maxPE < 8.
Nothing else outside the ECal selection.

  BDT, cut and count  from ntuple_cnc_bdt/ (CnCNtuple with trackerVeto and
                      bdtDisc), so N_straight can simply be left out
  ParticleNet         PNetCutFlow_RecoilX in analysis_aligned/: acceptance,
                      trigger, hit + loose preselection, ParticleNet, HCal. It
                      never had an N_straight or tracker-veto step

Closure rows first, which must reproduce numbers already in the talk:
  BDT with N_straight < 3, no tracker veto  -> 1.36 total, 69.2/72.6/75.9/69.4
  CnC re-optimized with N_straight < 2      -> 3.13 total, 64.2/68.1/69.3/62.0

Full sample throughout, like every other number in the talk.
Usage: eval_notrk_nostraight.py [ntuple_dir] [histo_tree]
"""
import glob
import sys

import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kFatal

NT = sys.argv[1] if len(sys.argv) > 1 else 'ntuple_cnc_bdt'
HT = sys.argv[2] if len(sys.argv) > 2 else 'analysis_aligned'
sys.stderr.write('ntuple %s/, histograms %s/\n' % (NT, HT))

TGT = 1.5e14
PRES = '/sdf/data/ldmx/private_production/mc26/pres_skim/'
RECO = '/sdf/data/ldmx/private_production/mc26/reco_v492/'
BKGS = [('ecal_pn_v15_8gev', 1.5e14), ('ecal_conversion_v15_8gev', 1.0e15),
        ('target_pn_v15_8gev', 1.0e15), ('target_conversion_v15_8gev', 1.0e15)]
SIGS = [('0.001', 0.8641), ('0.01', 0.8578), ('0.1', 0.8672), ('1.0', 0.8648)]
BDT_CUT = 0.954651

OPT = [('summedDet', 5101.6949152542375), ('summedTightIso', 1600.0),
       ('ecalBackEnergy', 500.0), ('nReadoutHits', 57.0), ('showerRMS', 220.0),
       ('maxCellDep', 600.0), ('stdLayerHit', 10.0)]

BASE = 'trigger && acceptance && nReadoutHits >= 1 && hcalMaxPE < 8'
OPT_SEL = ' && '.join('%s < %r' % kv for kv in OPT)
ROWS = [
    ('closure', 'BDT, N_straight < 3', 'bdtDisc > %r && nStraight < 3' % BDT_CUT),
    ('closure', 'CnC re-opt, N_straight < 2', OPT_SEL + ' && nStraight < 2'),
    ('NEW', 'BDT, no N_straight', 'bdtDisc > %r' % BDT_CUT),
    ('NEW', 'CnC re-opt, no N_straight', OPT_SEL),
]


def coverage(sub):
    ni = len(glob.glob(PRES + sub + '/*.root'))
    no = len(glob.glob(RECO + sub + '/*_reco.root'))
    return float(ni) / no if (ni and no) else 1.0


WEIGHT = {s: TGT / e * coverage(s) for s, e in BKGS}


def chain(sample):
    c = ROOT.TChain('CnCNtuple/cnc')
    if not c.Add('%s/%s/*_histo.root' % (NT, sample)):
        raise SystemExit('no files for %s' % sample)
    return c


def main():
    ch = {s: chain(s) for s, _ in BKGS}
    ch.update({m: chain('signal_v15_8gev/' + m) for m, _ in SIGS})
    den = {m: ch[m].GetEntries('acceptance') for m, _ in SIGS}

    for tag, desc, sel in ROWS:
        full = BASE + ' && ' + sel
        raw = {s: ch[s].GetEntries(full) for s, _ in BKGS}
        epn = raw['ecal_pn_v15_8gev'] * WEIGHT['ecal_pn_v15_8gev']
        tot = sum(raw[s] * WEIGHT[s] for s, _ in BKGS)
        effs = [100.0 * t * ch[m].GetEntries(full) / den[m] for m, t in SIGS]
        print('%-7s %-28s ECal PN raw %3d -> %6.2f   all %6.2f   signal %s   raw %s'
              % (tag, desc, raw['ecal_pn_v15_8gev'], epn, tot,
                 ' / '.join('%.1f%%' % e for e in effs),
                 ' '.join('%s=%d' % (s.split('_v15')[0], raw[s]) for s, _ in BKGS)))
        sys.stdout.flush()

    # ParticleNet: the original flow, which has neither cut
    tot, epn, effs = 0.0, 0.0, []
    for s, _ in BKGS:
        f = ROOT.TFile.Open('%s/%s_histos.root' % (HT, s))
        px = f.Get('CutBasedDM').Get('PNetCutFlow_RecoilX').ProjectionX()
        n = px.GetBinContent(5)
        tot += n * WEIGHT[s]
        if s == 'ecal_pn_v15_8gev':
            epn = n * WEIGHT[s]
        f.Close()
    for m, t in SIGS:
        f = ROOT.TFile.Open('%s/signal_v15_8gev_%s_histos.root' % (HT, m))
        px = f.Get('CutBasedDM').Get('PNetCutFlow_RecoilX').ProjectionX()
        effs.append(100.0 * t * px.GetBinContent(5) / px.GetBinContent(1))
        f.Close()
    print('%-7s %-28s ECal PN %6.2f   all %6.2f   signal %s'
          % ('NEW', 'ParticleNet (no N_straight)', epn, tot,
             ' / '.join('%.1f%%' % e for e in effs)))


if __name__ == '__main__':
    main()
