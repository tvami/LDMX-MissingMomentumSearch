#!/usr/bin/env python3
"""Re-optimize the cut-and-count thresholds with the Punzi FOM (PLAN_CNC_PUNZI.md).

  --step prepare   full pass over ntuple_cnc/: per-chunk entry check against
                   analysis/, coverage, v14 closure test, reduced-row cache
  --step optimize  coordinate ascent on the cache, train on even eventNumber
  --step report    full-pass cutflow at the new thresholds (test half), the
                   text and tex deliverables, and the two plots

Primary result: a = 3 with N_hits >= 1 (--a, --minhits); a = 2, 5 are a
sensitivity check only. Everything is a command-line flag: denv does not copy
env vars.
"""
import argparse
import glob
import json
import math
import os
import sys

import numpy as np

TGT = 1.5e14
RECO = '/sdf/data/ldmx/private_production/mc26/reco_v492/'
PRES = '/sdf/data/ldmx/private_production/mc26/pres_skim/'

# stem, ntuple subdir, sample EoT (None = signal), files per chunk
SAMPLES = [
    ('ecal_pn_v15_8gev',           'ecal_pn_v15_8gev',           1.5e14, 20),
    ('ecal_conversion_v15_8gev',   'ecal_conversion_v15_8gev',   1.0e15, 20),
    ('target_pn_v15_8gev',         'target_pn_v15_8gev',         1.0e15, 20),
    ('target_conversion_v15_8gev', 'target_conversion_v15_8gev', 1.0e15, 20),
    ('signal_v15_8gev_0.001', 'signal_v15_8gev/0.001', None, 1),
    ('signal_v15_8gev_0.01',  'signal_v15_8gev/0.01',  None, 1),
    ('signal_v15_8gev_0.1',   'signal_v15_8gev/0.1',   None, 1),
    ('signal_v15_8gev_1.0',   'signal_v15_8gev/1.0',   None, 1),
]
BKGS = [s[0] for s in SAMPLES if s[2]]
SIGS = [s[0] for s in SAMPLES if not s[2]]
TRIG = {'signal_v15_8gev_0.001': 0.8641, 'signal_v15_8gev_0.01': 0.8578,
        'signal_v15_8gev_0.1': 0.8672, 'signal_v15_8gev_1.0': 0.8648}
MASS = {'signal_v15_8gev_0.001': '1 MeV', 'signal_v15_8gev_0.01': '10 MeV',
        'signal_v15_8gev_0.1': '100 MeV', 'signal_v15_8gev_1.0': '1000 MeV'}

# name, v14 threshold (x < thr), integer, tex label
CUTS = [
    ('summedDet',      3500., False, r'$E_\mathrm{sum}$'),
    ('summedTightIso',  800., False, r'$E_\mathrm{sumTight}$'),
    ('ecalBackEnergy',  250., False, r'$E_\mathrm{back}$'),
    ('nReadoutHits',     70,  True,  r'$N_\mathrm{hits}$'),
    ('showerRMS',       110., False, r'$\mathrm{RMS}_\mathrm{shower}$'),
    ('maxCellDep',      300., False, r'$E_\mathrm{cell,max}$'),
    ('stdLayerHit',       5., False, r'$\mathrm{RMS}_\mathrm{Layer,hit}$'),
    ('nStraight',         3,  True,  r'$N_\mathrm{straight}$'),
    ('hcalMaxPE',         8,  True,  r'HCal maxPE'),
]
NV = len(CUTS)
IH = NV - 1                      # HCal index
V14 = np.array([c[1] for c in CUTS], dtype=float)
LOOSE = 2 * V14                  # scan ranges stop at 2x v14
NGRID = 60
UL90 = 2.303                     # 90% CL upper limit on zero observed


def say(*a):
    print(*a)
    sys.stdout.flush()


# ---------------------------------------------------------------- full pass
def reader():
    import ROOT
    ROOT.gROOT.SetBatch(True)
    ROOT.gInterpreter.Declare(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                'cnc_reader.C')).read())
    return ROOT


def files_of(args, sub):
    return sorted(glob.glob(os.path.join(args.ntuple, sub, '*_histo.root')))


def run_flow(ROOT, files, thr_sets, minhits, dump=''):
    """counts[set, parity, stage] over a full pass."""
    vs = ROOT.std.vector('std::string')()
    for f in files:
        vs.push_back(f)
    vt = ROOT.std.vector('double')()
    for t in thr_sets:
        for x in t:
            vt.push_back(float(x))
    vm = ROOT.std.vector('int')()
    for m in minhits:
        vm.push_back(int(m))
    vl = ROOT.std.vector('double')()
    for x in LOOSE:
        vl.push_back(float(x))
    out = ROOT.cnc.flow(vs, vt, vm, vl, dump)
    return np.array(list(out)).reshape(len(minhits), 2, 3 + NV)


def coverage(sub):
    ni = len(glob.glob(PRES + sub + '/*.root'))
    no = len(glob.glob(RECO + sub + '/*_reco.root'))
    return (float(ni) / no) if (ni and no) else 1.0, ni, no


def chunk_check(ROOT, args, stem, sub, per):
    """Entries per ntuple chunk against the same chunk of analysis/ (every
    event fills TrigEffVsMissingE once) and the expected chunk count."""
    nreco = len(glob.glob(RECO + sub + '/*_reco.root'))
    expect = (nreco + per - 1) // per
    bad, n = [], 0
    for f in files_of(args, sub):
        n += 1
        a = os.path.join(args.ana, sub, os.path.basename(f))
        tf = ROOT.TFile.Open(f)
        t = tf.Get('CnCNtuple/cnc') if tf else None
        ne = t.GetEntries() if t else -1
        ta = ROOT.TFile.Open(a) if os.path.exists(a) else None
        h = ta.Get('CutBasedDM/TrigEffVsMissingE') if ta else None
        na = h.GetEntries() if h else -1
        if ne != na:
            bad.append((os.path.basename(f), ne, na))
        if tf: tf.Close()
        if ta: ta.Close()
    return n, expect, bad


def step_prepare(args):
    ROOT = reader()
    os.makedirs(os.path.join(args.ntuple, 'cache'), exist_ok=True)
    info, ok = {}, True
    closure = []
    for stem, sub, eot, per in SAMPLES:
        n, expect, bad = chunk_check(ROOT, args, stem, sub, per)
        say('%-28s chunks %d / %d expected, %d entry mismatches vs %s/'
            % (stem, n, expect, len(bad), args.ana))
        for b in bad[:10]:
            say('   MISMATCH %s ntuple %d analysis %d' % b)
        ok &= (n == expect and not bad)
        cov, ni, no = coverage(sub)
        w = TGT / eot * cov if eot else 1.0
        dump = os.path.join(args.ntuple, 'cache', stem + '.bin')
        c = run_flow(ROOT, files_of(args, sub), [V14, V14], [0, 1], dump)
        info[stem] = dict(coverage=cov, pres=ni, reco=no, eot=eot, weight=w,
                          flow_v14=c[0].tolist(), flow_v14_hit=c[1].tolist(),
                          nrows=os.path.getsize(dump) // (4 * (NV + 1)))
        say('   weight %.4f (coverage %d/%d), cached rows %d'
            % (w, ni, no, info[stem]['nrows']))
        closure.append((stem, c[0].sum(axis=0)))
    json.dump(info, open(os.path.join(args.ntuple, 'cache', 'info.json'), 'w'), indent=1)

    # closure: raw v14 flow against CnCCutFlow_RecoilX of the talk's files
    say('\n=== closure test: v14 thresholds, raw counts, ntuple vs %s/ ===' % args.ana)
    passed = True
    for stem, cnt in closure:
        f = ROOT.TFile.Open(os.path.join(args.ana, stem + '_histos.root'))
        px = f.Get('CutBasedDM/CnCCutFlow_RecoilX').ProjectionX()
        ref = [px.GetBinContent(i + 1) for i in range(11)]
        f.Close()
        mine = [cnt[0], cnt[1]] + list(cnt[3:])     # skip the hit stage
        same = all(abs(a - b) < 0.5 for a, b in zip(mine, ref))
        passed &= same
        say('%-28s %s' % (stem, 'PASS' if same else 'FAIL'))
        if not same:
            for i, (a, b) in enumerate(zip(mine, ref)):
                say('   bin %2d ntuple %12d ref %12d %s' % (i, a, b, '' if a == b else '<--'))
    # the talk's headline numbers, at 1.5e14 EoT
    say('\nv14 at 1.5e14 EoT: ' + ', '.join(
        '%s %.2f' % (b, closure[i][1][-1] * info[b]['weight']) for i, b in enumerate(BKGS)))
    say('v14 signal eff: ' + ' / '.join(
        '%.1f%%' % (100 * TRIG[s] * cnt[-1] / cnt[0]) for s, cnt in closure if s in SIGS))
    say('\nCLOSURE %s, chunk check %s' % ('PASS' if passed else 'FAIL', 'PASS' if ok else 'FAIL'))


# ---------------------------------------------------------------- optimizer
class Data:
    """Reduced rows for train or test, with per-row weights."""

    def __init__(self, args, half):
        info = json.load(open(os.path.join(args.ntuple, 'cache', 'info.json')))
        self.info = info
        self.half = half
        xs, ws = [], []
        self.raw_w = {}
        self.sig = {}
        for b in BKGS:
            x, f = self._load(args, b, info, half)
            w = info[b]['weight'] * f
            self.raw_w[b] = w
            xs.append(x)
            ws.append(np.full(len(x), w))
            self.__dict__.setdefault('bkg_parts', []).append((b, len(x)))
        self.xb = np.concatenate(xs)
        self.wb = np.concatenate(ws)
        self.tagb = np.concatenate([np.full(n, i) for i, (b, n) in enumerate(self.bkg_parts)])
        for s in SIGS:
            x, _ = self._load(args, s, info, half)
            fl = np.array(info[s]['flow_v14'])
            nacc = fl[:, 0].sum() if half == 'all' else fl[0 if half == 'train' else 1, 0]
            self.sig[s] = (x, TRIG[s] / nacc)

    @staticmethod
    def _load(args, stem, info, half):
        a = np.fromfile(os.path.join(args.ntuple, 'cache', stem + '.bin'),
                        dtype=np.float32).reshape(-1, NV + 1)
        fl = np.array(info[stem]['flow_v14'])
        nall = fl[:, 0].sum()
        if half == 'all':
            return a[:, :NV].astype(np.float64), 1.0
        p = 0 if half == 'train' else 1
        # scale the half back to the full sample, exactly rather than x2
        return a[a[:, NV] == p, :NV].astype(np.float64), nall / fl[p, 0]

    def restrict(self, hcal_free):
        """Drop rows that no grid point can pass: any x >= LOOSE, or HCal >= v14
        when it is fixed. Exact for the optimizer, not for N-1 or drop-one."""
        top = LOOSE.copy()
        if not hcal_free:
            top[IH] = V14[IH]
        m = np.all(self.xb < top, axis=1)
        self.xb, self.wb, self.tagb = self.xb[m], self.wb[m], self.tagb[m]
        for s, (x, k) in self.sig.items():
            self.sig[s] = (x[np.all(x < top, axis=1)], k)
        return self

    def passes(self, x, thr, minhits):
        return np.all(x < thr, axis=1) & (x[:, 3] >= minhits)

    def yields(self, thr, minhits):
        pb = self.passes(self.xb, thr, minhits)
        B = self.wb[pb].sum()
        nb = {b: int((pb & (self.tagb == i)).sum()) for i, b in enumerate(BKGS)}
        eps = {s: self.passes(x, thr, minhits).sum() * k for s, (x, k) in self.sig.items()}
        return B, nb, eps


def fom(eps, B, a):
    return eps / (a / 2.0 + math.sqrt(max(B, 0.0)))


def make_grids(d):
    grids = []
    allx = np.concatenate([d.xb] + [x for x, _ in d.sig.values()])
    for k, (name, v, isint, _) in enumerate(CUTS):
        lo = max(float(allx[:, k].min()), 0.0)
        g = np.linspace(lo, LOOSE[k], NGRID)
        if isint:
            g = np.round(g)
        g = np.unique(np.append(g, V14[k]))
        grids.append(g)
    return grids


def scan_cut(d, thr, k, grid, minhits, a, masses):
    """FOM for every grid value of cut k with the others fixed."""
    others = [j for j in range(NV) if j != k]

    def cum(x, w):
        m = np.all(x[:, others] < thr[others], axis=1) & (x[:, 3] >= minhits)
        xs = x[m, k]
        o = np.argsort(xs)
        cw = np.concatenate([[0.0], np.cumsum(w[m][o] if w is not None else np.ones(m.sum()))])
        return cw[np.searchsorted(xs[o], grid, side='left')]

    B = cum(d.xb, d.wb)
    eps = np.zeros(len(grid))
    for s in masses:
        x, kf = d.sig[s]
        eps += cum(x, None) * kf
    eps /= len(masses)
    return eps / (a / 2.0 + np.sqrt(np.maximum(B, 0)))


def pick(f):
    """Middle of the plateau holding the first maximum, so ties do not drift
    to an edge tuned on a single event."""
    m = f.max()
    i = int(np.argmax(f))
    j = i
    while j + 1 < len(f) and f[j + 1] >= m * (1 - 1e-12):
        j += 1
    return (i + j) // 2


def ascend(d, grids, start, minhits, a, masses, free):
    thr = start.copy()
    B, _, eps = d.yields(thr, minhits)
    hist = [fom(np.mean([eps[s] for s in masses]), B, a)]   # sweep 0 = start
    for sweep in range(20):
        moved = False
        for k in free:
            f = scan_cut(d, thr, k, grids[k], minhits, a, masses)
            new = grids[k][pick(f)]
            if new != thr[k]:
                thr[k] = new
                moved = True
        B, _, eps = d.yields(thr, minhits)
        hist.append(fom(np.mean([eps[s] for s in masses]), B, a))
        if not moved:
            break
    return thr, hist


def optimize_one(args, cfg, d=None):
    d = d or Data(args, 'train')
    # grids from the full rows, then restrict
    grids = make_grids(d)
    d.restrict(cfg['hcal_free'])
    say('%s: %d bkg rows after restrict' % (cfg['name'], len(d.xb)))
    free = list(range(NV)) if cfg['hcal_free'] else list(range(IH))
    rng = np.random.default_rng(cfg['seed'])
    best = None
    runs = []
    for i in range(args.nseeds + 1):
        start = V14.copy()
        if i > 0:
            for k in free:
                start[k] = grids[k][rng.integers(len(grids[k]))]
        thr, hist = ascend(d, grids, start, cfg['minhits'], cfg['a'], cfg['masses'], free)
        runs.append(dict(seed=i, hist=hist, thr=thr.tolist()))
        if best is None or hist[-1] > best[1][-1] + 1e-15:
            best = (thr, hist, i)
    return dict(cfg, thr=best[0].tolist(), hist=best[1], best_seed=best[2], runs=runs)


def configs(args):
    """Primary: a = args.a, N_hits >= args.minhits. Other a values are only a
    sensitivity check."""
    mh, A = args.minhits, args.a
    run = 'nhits>=%d' % mh if mh else 'chain'
    out = []
    for a in sorted({2, 3, 5, A}):
        out.append(dict(name='%s a=%d' % (run, a), minhits=mh, a=a, primary=(a == A),
                        hcal_free=False, masses=SIGS, seed=100 * mh + a))
    out.append(dict(name='%s a=%d HCal free' % (run, A), minhits=mh, a=A, primary=False,
                    hcal_free=True, masses=SIGS, seed=100 * mh + 7))
    for s in SIGS:
        out.append(dict(name='%s a=%d only %s' % (run, A, MASS[s]), minhits=mh, a=A,
                        primary=False, hcal_free=False, masses=[s], seed=100 * mh + 11))
    return out


def _worker(job):
    args, cfg = job
    return optimize_one(args, cfg)


def step_optimize(args):
    from multiprocessing import Pool
    cf = configs(args)
    say('%d configurations x %d random seeds (+ v14 seed), %d workers'
        % (len(cf), args.nseeds, args.nproc))
    with Pool(args.nproc) as p:
        res = p.map(_worker, [(args, c) for c in cf], chunksize=1)
    json.dump(res, open(os.path.join(args.out, 'cnc_punzi_results.json'), 'w'), indent=1)
    for r in res:
        say('%-28s FOM %.5f seed %d sweeps %d' % (r['name'], r['hist'][-1], r['best_seed'], len(r['hist'])))


# ---------------------------------------------------------------- report
def fmt_thr(k, v):
    return '%d' % v if CUTS[k][2] else '%.4g' % v


def ycell(n, w):
    """Test-half background cell: zero observed gets the 90% CL limit."""
    if n == 0:
        return '0 ($<$%.1f)' % (UL90 * w)
    x = n * w
    return '{:,.0f}'.format(x) if x >= 10 else '%.1f' % x


def step_report(args):
    res = json.load(open(os.path.join(args.out, 'cnc_punzi_results.json')))
    tr, te = Data(args, 'train'), Data(args, 'test')
    info = tr.info

    def summary(r, d):
        thr = np.array(r['thr'])
        B, nb, eps = d.yields(thr, r['minhits'])
        e = np.mean([eps[s] for s in r['masses']])
        return B, nb, eps, fom(e, B, r['a'])

    # 1. thresholds
    L = []
    L.append('# Punzi FOM eps/(a/2+sqrt(B)), B at 1.5e14 EoT, train = even eventNumber')
    L.append('# eps = trig_eff * N(pass)/N(acceptance), mean over masses unless "only"')
    L.append('# weights per event (full sample): ' + ', '.join(
        '%s %.4f' % (b, info[b]['weight']) for b in BKGS))
    hdr = '%-28s' % 'config' + ''.join('%16s' % c[0] for c in CUTS)
    L.append(hdr)
    L.append('%-28s' % 'v14' + ''.join('%16s' % fmt_thr(k, v) for k, v in enumerate(V14)))
    for r in res:
        L.append('%-28s' % r['name'] + ''.join('%16s' % fmt_thr(k, v) for k, v in enumerate(r['thr'])))
    # drop one cut at a time at the optimum: what each cut buys (train half)
    L.append('\n# drop-one at the primary optimum, train half: FOM ratio, B, mean eff')
    for r in res:
        if not r.get('primary'):
            continue
        thr0 = np.array(r['thr'])
        B0, _, e0, F0 = summary(r, tr)
        L.append('%s: FOM %.5f  B %.2f  eff %.1f%%' % (r['name'], F0, B0, 100 * np.mean(list(e0.values()))))
        for k, c in enumerate(CUTS):
            t = thr0.copy(); t[k] = np.inf
            B, _, e, F = summary(dict(r, thr=t.tolist()), tr)
            L.append('   without %-15s FOM x%.3f  B %10.2f  eff %.1f%%'
                     % (c[0], F / F0, B, 100 * np.mean(list(e.values()))))
    open(os.path.join(args.out, 'cnc_punzi_thresholds.txt'), 'w').write('\n'.join(L) + '\n')

    # 2. train vs test
    L = ['# train = even eventNumber, test = odd; each half scaled to the full sample',
         '# B at 1.5e14 EoT; raw = unweighted events in that half; ECal PN weighs %.3f per test event'
         % te.raw_w['ecal_pn_v15_8gev']]
    v14 = dict(name='v14', thr=V14.tolist(), minhits=0, a=args.a, masses=SIGS)
    v14h = dict(v14, name='v14 + nhits>=1', minhits=1)
    for r in [v14, v14h] + res:
        L.append('\n== %s ==' % r['name'])
        L.append('thresholds: ' + ', '.join('%s<%s' % (c[0], fmt_thr(k, r['thr'][k]))
                                          for k, c in enumerate(CUTS)))
        for lab, d in (('train', tr), ('test', te)):
            B, nb, eps, F = summary(r, d)
            raw = ' '.join('%s=%d' % (b.split('_v15')[0], nb[b]) for b in BKGS)
            ul = ''
            if nb['ecal_pn_v15_8gev'] == 0:
                ul = '  (ECal PN 0 observed, 90%% CL < %.1f)' % (UL90 * d.raw_w['ecal_pn_v15_8gev'])
            L.append('  %-5s FOM %.5f  B %8.2f  raw[%s]  eff %s%s' % (
                lab, F, B, raw, ' / '.join('%.1f%%' % (100 * eps[s]) for s in SIGS), ul))
    open(os.path.join(args.out, 'cnc_punzi_train_vs_test.txt'), 'w').write('\n'.join(L) + '\n')

    # 3. full-pass cutflow table, test half, primary result
    ROOT = reader()
    pick_cfg = [r for r in res if r.get('primary')]
    thr_sets = [r['thr'] for r in pick_cfg]
    mh = [r['minhits'] for r in pick_cfg]
    flows = {}
    for stem, sub, eot, per in SAMPLES:
        flows[stem] = run_flow(ROOT, files_of(args, sub), thr_sets, mh)
    T = []
    for i, r in enumerate(pick_cfg):
        thr = r['thr']
        T.append('%%%%%% Punzi a=%d, %s, test half (odd eventNumber), 1.5e14 EoT' % (r['a'], r['name']))
        T.append('%% raw ECal PN test events at the last row: %d' % flows[BKGS[0]][i, 1, -1])
        T.append(r'\begin{tabular}{lrrcccc}')
        T.append(r'\toprule')
        T.append(r'cut & \ecal\ PN & \ecal\ conv. & 1\,MeV & 10\,MeV & 100\,MeV & 1000\,MeV \\')
        T.append(r'\midrule')
        rows = [(0, 'All / Acceptance'), (1, 'Triggered')]
        if r['minhits']:
            rows.append((2, r'$N_\mathrm{hits} \geq 1$'))
        for k, c in enumerate(CUTS):
            rows.append((3 + k, '%s $<$ %s' % (c[3], fmt_thr(k, thr[k]))))
        for st, lab in rows:
            cells = []
            for b in BKGS[:2]:
                fl = flows[b][i]
                f = fl[:, 0].sum() / fl[1, 0]
                cells.append(ycell(int(fl[1, st]), info[b]['weight'] * f))
            for s in SIGS:
                fl = flows[s][i]
                cells.append('%.1f\\%%' % (100 * TRIG[s] * fl[1, st] / fl[1, 0]))
            if st == 3 + IH:
                T.append(r'\midrule')
            T.append('%-40s & %s \\\\' % (lab, ' & '.join(cells)))
        T.append(r'\bottomrule')
        T.append(r'\end{tabular}')
        tg = ', '.join('%s %s' % (b.split('_v15')[0], ycell(
            int(flows[b][i][1, -1]), info[b]['weight'] * flows[b][i][:, 0].sum() / flows[b][i][1, 0]))
            for b in BKGS[2:])
        T.append('%% last row, not shown: ' + tg)
        T.append('')
    open(os.path.join(args.out, 'cnc_punzi_table.tex'), 'w').write('\n'.join(T) + '\n')

    plot_fom(args, res)
    plot_nminus1(args, pick_cfg)
    say('report written to %s/ and %s/' % (args.out, args.plots))


def plot_fom(args, res):
    import ROOT
    import ldmx_plot_style as st
    st.init()
    c = st.canvas('cfom', logy=False)
    keep = []
    sel = [r for r in res if r.get('primary')]
    ymax = max(max(x['hist']) for r in sel for x in r['runs']) * 1.3
    nmax = max(len(x['hist']) for r in sel for x in r['runs'])
    fr = c.DrawFrame(-0.5, 0, nmax - 0.5, ymax)
    fr.GetXaxis().SetTitle('sweep (0 = seed)')
    fr.GetXaxis().SetNdivisions(nmax, False)
    fr.GetYaxis().SetTitle('Punzi FOM (train, a = %d)' % sel[0]['a'])
    leg = st.make_legend(30, ncol=1)
    for ir, r in enumerate(sel):
        col = ROOT.TColor.GetColor(st.COLORS[ir])
        for x in r['runs']:
            g = ROOT.TGraph(len(x['hist']))
            for i, v in enumerate(x['hist']):
                g.SetPoint(i, i, v)
            best = x['seed'] == r['best_seed']
            g.SetLineColorAlpha(col, 1.0 if best else 0.25)
            g.SetMarkerColor(col)
            g.SetLineWidth(3 if best else 1)
            g.SetMarkerStyle(20 if best else 1)
            g.Draw('LP' if best else 'L')
            keep.append(g)
            if best:
                leg.AddEntry(g, '%s, best of %d seeds' % (r['name'], len(r['runs'])), 'LP')
    leg.Draw()
    keep += st.stamps(sample='ntuple_cnc, train half')
    for t in keep[-4:]:
        t.Draw()
    for ext in ('pdf', 'png'):
        c.SaveAs('%s/cnc_punzi_fom.%s' % (args.plots, ext))


# x range shown per variable, as plot_cnc_vars.py
XR = [(0, 10000), (0, 3000), (0, 1500), (0, 150), (0, 250), (0, 800), (0, 20), (0, 10), (0, 40)]
XT = ['E_{sum} [MeV]', 'E_{sum, tight iso} [MeV]', 'E_{back} [MeV]', 'N_{hits}',
      'shower RMS [mm]', 'E_{cell, max} [MeV]', 'RMS of hit layers', 'N_{straight tracks}', 'HCal max PE']


def plot_nminus1(args, cfgs):
    import ROOT
    import ldmx_plot_style as st
    st.init()
    d = Data(args, 'all')
    for r in cfgs:
        thr = np.array(r['thr'])
        tag = ''
        c = ROOT.TCanvas('cn1' + tag, '', 1800, 1020)
        grid = ROOT.TPad('grid' + tag, '', 0.0, 0.0, 1.0, 0.93)
        grid.Draw()
        grid.Divide(3, 3)
        keep = [grid]
        for k in range(NV):
            p = grid.cd(k + 1)
            p.SetLogy()
            p.SetLeftMargin(0.14); p.SetRightMargin(0.07)
            p.SetBottomMargin(0.17); p.SetTopMargin(0.09)
            others = [j for j in range(NV) if j != k]
            lo, hi = XR[k]
            nb = int(hi - lo) if CUTS[k][2] else 50
            series = [('bkg', d.xb, d.wb, st.BKG_COLOR, 'Background (all four)')]
            for s, ci in (('signal_v15_8gev_0.001', 0), ('signal_v15_8gev_1.0', 3)):
                x, kf = d.sig[s]
                series.append((s, x, None, st.COLORS[ci], st.label_for(s)))
            first, panel = True, []
            for name, x, w, col, lab in series:
                m = np.all(x[:, others] < thr[others], axis=1) & (x[:, 3] >= r['minhits'])
                h = ROOT.TH1D('h%s%d%s' % (name, k, tag), '', nb, lo - (0.5 if CUTS[k][2] else 0),
                              hi - (0.5 if CUTS[k][2] else 0))
                h.Sumw2()
                xs = x[m, k]
                ws = w[m] if w is not None else np.ones(len(xs))
                ax = h.GetXaxis()
                # overflow folded into the last bin, as add_overflow does
                xc = np.clip(xs, ax.GetXmin(), ax.GetXmax() - 1e-6 * ax.GetBinWidth(1))
                cw, _ = np.histogram(xc, bins=nb, range=(ax.GetXmin(), ax.GetXmax()), weights=ws)
                c2, _ = np.histogram(xc, bins=nb, range=(ax.GetXmin(), ax.GetXmax()), weights=ws ** 2)
                for ib in range(nb):
                    h.SetBinContent(ib + 1, cw[ib])
                    h.SetBinError(ib + 1, c2[ib] ** 0.5)
                st.normalize(h)
                kind = 'point'
                if name == 'bkg':
                    st.style_bkg(h, col, marker_size=0.6)
                    kind = 'fill'
                else:
                    st.style_signal(h, col, marker_size=0.6)
                if first:
                    st.style_axes(h, XT[k], ymin=1e-5, ymax=100,
                                  title_size=0.07, label_size=0.06)
                h.Draw(st.draw_opt(first, kind))
                first = False
                panel.append((h, lab, kind))
            keep += [h for h, _, _ in panel]
            for v, style in ((V14[k], ROOT.kDotted), (thr[k], ROOT.kDashed)):
                ln = st.dashed_line()
                ln.SetLineStyle(style)
                ln.DrawLine(v, 1e-5, v, 100)
                keep.append(ln)
            t = ROOT.TLatex()
            t.SetNDC(); t.SetTextFont(42); t.SetTextSize(0.07)
            t.DrawLatex(0.17, 0.925, 'cut at %s (v14 %s)' % (fmt_thr(k, thr[k]), fmt_thr(k, V14[k])))
            keep.append(t)
            if k == 0:
                leg = ROOT.TLegend(0.40, 0.70, 0.93, 0.91, '', 'brNDC')
                leg.SetBorderSize(0); leg.SetFillStyle(0)
                leg.SetTextFont(42); leg.SetTextSize(0.058)
                for h, lab, kind in panel:
                    leg.AddEntry(h, lab, st.legend_opt(kind))
                leg.Draw()
                keep.append(leg)
        c.cd(0)
        texts = st.stamps(sample=r['name'], scale=0.75)
        for t in texts:
            t.SetY(0.955)
            t.Draw()
        for ext in ('pdf', 'png'):
            c.SaveAs('%s/cnc_punzi_nminus1%s.%s' % (args.plots, tag, ext))


def step_fullstat(args):
    """Primary thresholds and v14 (same hit requirement) on all events, both
    halves. Train half was used to pick the cuts, so this is biased low."""
    res = json.load(open(os.path.join(args.out, 'cnc_punzi_results.json')))
    r = [x for x in res if x.get('primary')][0]
    info = json.load(open(os.path.join(args.ntuple, 'cache', 'info.json')))
    ROOT = reader()
    sets = [V14.tolist(), r['thr']]
    mh = [r['minhits'], r['minhits']]
    flows = {stem: run_flow(ROOT, files_of(args, sub), sets, mh)
             for stem, sub, eot, per in SAMPLES}

    def bcell(n, w):
        if n == 0:
            return '0 ($<$%.1f)' % (UL90 * w)
        x = n * w
        return '{:,.0f}'.format(x) if x >= 10 else '%.1f' % x

    T, L = [], []
    for i, lab in enumerate(['v14', r['name']]):
        thr = sets[i]
        L.append('== %s, N_hits >= %d, full statistics ==' % (lab, r['minhits']))
        for b in BKGS:
            fl = flows[b][i]
            L.append('  %-28s raw train %d test %d all %d -> %.2f at 1.5e14 EoT'
                     % (b, fl[0, -1], fl[1, -1], fl[:, -1].sum(), fl[:, -1].sum() * info[b]['weight']))
        L.append('  total B %.2f' % sum(flows[b][i][:, -1].sum() * info[b]['weight'] for b in BKGS))
        L.append('  eff ' + ' / '.join('%.1f%%' % (100 * TRIG[s] * flows[s][i][:, -1].sum()
                                                   / flows[s][i][:, 0].sum()) for s in SIGS))
        T.append('%%%%%% %s, N_hits >= %d, full statistics (both halves), 1.5e14 EoT' % (lab, r['minhits']))
        T.append(r'\begin{tabular}{lrrcccc}')
        T.append(r'\toprule')
        T.append(r'cut & \ecal\ PN & \ecal\ conv. & 1\,MeV & 10\,MeV & 100\,MeV & 1000\,MeV \\')
        T.append(r'\midrule')
        rows = [(0, 'All / Acceptance'), (1, 'Triggered'), (2, r'\ecal\ hits $\geq$ 1')]
        for k, c in enumerate(CUTS):
            rows.append((3 + k, '%s $<$ %s' % (c[3], fmt_thr(k, thr[k]))))
        for st, rl in rows:
            cells = [bcell(int(flows[b][i][:, st].sum()), info[b]['weight']) for b in BKGS[:2]]
            cells += ['%.1f\\%%' % (100 * TRIG[s] * flows[s][i][:, st].sum() / flows[s][i][:, 0].sum())
                      for s in SIGS]
            if st == 3 + IH:
                T.append(r'\midrule')
            T.append('%-40s & %s \\\\' % (rl, ' & '.join(cells)))
        T.append(r'\bottomrule')
        T.append(r'\end{tabular}')
        T.append('%% last row, not shown: ' + ', '.join('%s %s' % (b.split('_v15')[0], bcell(
            int(flows[b][i][:, -1].sum()), info[b]['weight'])) for b in BKGS[2:]))
        T.append('')
    open(os.path.join(args.out, 'cnc_punzi_table_full.tex'), 'w').write('\n'.join(T) + '\n')
    open(os.path.join(args.out, 'cnc_punzi_fullstat.txt'), 'w').write('\n'.join(L) + '\n')
    say('\n'.join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--step', required=True, choices=['prepare', 'optimize', 'report', 'fullstat'])
    ap.add_argument('--ntuple', default='ntuple_cnc')
    ap.add_argument('--ana', default='analysis', help='reference histograms for the closure')
    ap.add_argument('--out', default='scan_out')
    ap.add_argument('--plots', default='plots_pnet')
    ap.add_argument('--nseeds', type=int, default=20)
    ap.add_argument('--nproc', type=int, default=16)
    ap.add_argument('--a', type=int, default=3, help='Punzi a of the primary result')
    ap.add_argument('--minhits', type=int, default=1, help='require N_hits >= this')
    args = ap.parse_args()
    say('step %s: ntuple %s/, reference %s/, out %s/, plots %s/, seeds %d, a %d, minhits %d'
        % (args.step, args.ntuple, args.ana, args.out, args.plots, args.nseeds, args.a, args.minhits))
    os.makedirs(args.out, exist_ok=True)
    os.makedirs(args.plots, exist_ok=True)
    {'prepare': step_prepare, 'optimize': step_optimize, 'report': step_report,
     'fullstat': step_fullstat}[args.step](args)


if __name__ == '__main__':
    main()
