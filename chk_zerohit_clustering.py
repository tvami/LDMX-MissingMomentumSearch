#!/usr/bin/env python3
"""Are the zero-ECal-hit events and the survivors spread evenly over the files?

Uses analysis_pnetv11, which is complete (1185 chunks, same 5-file chunking as
analysis_nhits), so per-chunk numbers are available for every chunk:

  - zero-hit events per chunk, at the preselection stage of the standard flow
  - cut-and-count and PNet survivors per chunk (last bin of each flow)

If the zero-hit events are a physics population they should be spread roughly
evenly (Poisson). If a handful of chunks hold most of them, they point at a
production or reconstruction defect in specific runs instead.

Also reports how many survivors sit in the chunks the nhits run is still
missing, which is what the provisional peek did not see.
"""
import glob
import os
import sys

import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kFatal

ANA = 'analysis_pnetv11'
MISSING_LISTS = '/sdf/group/ldmx/users/tamasvami/slurm/filelists/nhrec_ecal_pn_v15_8gev'
STAGE = 3   # Preselection in the standard flow


def missing_chunk_names():
    names = set()
    for p in glob.glob(MISSING_LISTS + '/*.txt'):
        files = open(p).read().split()
        if files:
            names.add(os.path.basename(files[-1])[:-5] + '_histo.root')
    return names


def main():
    miss = missing_chunk_names()
    rows = []
    for p in sorted(glob.glob('%s/ecal_pn_v15_8gev/*_histo.root' % ANA)):
        f = ROOT.TFile.Open(p)
        if not f or f.IsZombie():
            continue
        d = f.Get('CutBasedDM')
        if not d:
            f.Close()
            continue
        nh = d.Get('NReadoutHits').ProjectionY('nh', STAGE + 1, STAGE + 1)
        zero = nh.GetBinContent(1)
        npres = nh.Integral(0, nh.GetNbinsX() + 1)
        cnc = d.Get('CnCCutFlow_RecoilX').ProjectionX('c').GetBinContent(11)
        pn = d.Get('PNetCutFlow_RecoilX').ProjectionX('p').GetBinContent(5)
        rows.append((os.path.basename(p), zero, npres, cnc, pn))
        f.Close()

    n = len(rows)
    tz = sum(r[1] for r in rows)
    tc = sum(r[3] for r in rows)
    tp = sum(r[4] for r in rows)
    print('chunks read: %d   zero-hit total: %.0f   CnC survivors: %.0f   '
          'PNet survivors: %.0f' % (n, tz, tc, tp))

    # concentration of zero-hit events
    zs = sorted((r[1] for r in rows), reverse=True)
    mean = tz / n if n else 0
    print()
    print('zero-hit events per chunk: mean %.1f, max %.0f' % (mean, zs[0]))
    for k in (1, 5, 10, 20, 50):
        print('  top %3d chunks hold %6.0f (%.0f%% of all zero-hit events)'
              % (k, sum(zs[:k]), 100 * sum(zs[:k]) / tz if tz else 0))
    nz = sum(1 for r in rows if r[1] > 0)
    print('  chunks with any zero-hit event: %d of %d' % (nz, n))

    print()
    print('top 10 chunks by zero-hit count:')
    print('  %-62s %7s %9s %4s %4s' % ('chunk', 'zero', 'presel', 'CnC', 'PNet'))
    for r in sorted(rows, key=lambda r: -r[1])[:10]:
        print('  %-62s %7.0f %9.0f %4.0f %4.0f' % r)

    # survivors in the chunks the nhits run has not finished
    mc = sum(r[3] for r in rows if r[0] in miss)
    mp = sum(r[4] for r in rows if r[0] in miss)
    mz = sum(r[1] for r in rows if r[0] in miss)
    print()
    print('in the %d chunks still missing from analysis_nhits: '
          'CnC %.0f, PNet %.0f, zero-hit %.0f' % (len(miss), mc, mp, mz))


if __name__ == '__main__':
    main()
