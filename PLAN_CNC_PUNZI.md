# Plan: re-optimize the cut-and-count with the Punzi FOM

Goal: replace the v14 cut-and-count thresholds with ones optimized on the v15
8 GeV samples, using the Punzi figure of merit, and quote the resulting
background and signal efficiency at 1.5e14 EoT in the same convention as the
talk tables.

This plan is written to run **in parallel** with the ParticleNet re-run
(`analysis_nhits/`, `CutBasedDM.cxx`). Section 1 lists what must not be touched
so the two cannot interfere.

All paths below are relative to
`/sdf/group/ldmx/users/tamasvami/ldmx-analysis/v4.9.2/ldmx-sw/LDMX-MissingMomentumSearch`
unless they start with `/`.

---

## 1. Rules for running alongside the PNet re-run

These are not style points; each one has broken a campaign before.

| rule | why |
| --- | --- |
| **Do not edit `CutBasedDM.cxx` or delete `libCutBasedDM.so`** | the PNet jobs load that library; `processor_from_file` recompiles when the source is newer, and parallel tasks racing on the compile corrupt it |
| **No git operations on the ldmx-sw source** while any job runs | a checkout changed the source under live jobs once and corrupted the library |
| New analyzer goes in its **own file with its own `.so`** (`CnCNtuple.cxx` / `libCnCNtuple.so`) | keeps the two campaigns fully independent |
| Compile `libCnCNtuple.so` **once, serially**, with a single-file unit test, before submitting anything | same compile race |
| Pass every switch as a **command-line argument**, never an env var | `denv_env_var_copy_all="false"`: exported variables never reach the container, and the default silently wins |
| Write output **only inside the ldmx-sw workspace** (`ntuple_cnc/`) | the container can only write there; the rest of `/sdf/group` is read-only inside it |
| Never write to `$HOME` | the home quota fills and jobs then die in 1 s with no log |
| Anything touching `/sdf/data` runs on `sdfiana006`/`sdfiana007` | not mounted elsewhere |
| Use SLURM job names prefixed `cnc_` and filelist tags prefixed `cncnt_` | so drains and recovery can tell the campaigns apart (section 7) |

---

## 2. Why the existing histograms are not enough

The talk's per-variable plots are **marginals**: each variable projected at one
fixed stage of the standard flow. Optimizing eight thresholds jointly needs the
**joint** distribution, since tightening one cut changes the population every
other cut sees. Re-filling histograms for every threshold combination is not
feasible.

So: write a flat ntuple of the cut variables once, then optimize offline in
numpy with no further reprocessing. Every threshold combination is then a
vectorized mask, about a second per evaluation.

The good news: none of the cut-and-count variables needs ParticleNet, so the
ntuple pass runs **without** it. At about 10 s per reco file that is roughly
20 CPU-hours for all samples, against ~580 for the PNet re-run. It will not
compete meaningfully for the queue.

---

## 3. Step A: the ntupler (`CnCNtuple.cxx`)

A minimal analyzer, loaded with `processor_from_file`, that writes one TTree
row per event into the histogram file (create the tree after
`getHistoDirectory()`, which is what `CutBasedDM` already calls in its start).

### Branches
| branch | type | source |
| --- | --- | --- |
| `summedDet` | float | `EcalVeto_reco.getSummedDet()` |
| `summedTightIso` | float | `getSummedTightIso()` |
| `ecalBackEnergy` | float | `getEcalBackEnergy()` |
| `nReadoutHits` | int | `getNReadoutHits()` |
| `showerRMS` | float | `getShowerRMS()` |
| `maxCellDep` | float | `getMaxCellDep()` |
| `stdLayerHit` | float | `getStdLayerHit()` |
| `nStraight` | int | `EcalMipInfo.getNStraightTracks()`, or -1 if absent |
| `hcalMaxPE` | float | **copied exactly** from `CutBasedDM.cxx` lines ~578-640 |
| `acceptance` | bool | same logic as `CutBasedDM` (truth fiducial for signal, true for background) |
| `trigger` | bool | `TriggerResult.passed()`, pass `sim` |
| `eventNumber` | int | event header, for the train/test split |

`hcalMaxPE` must be the identical definition, not a re-derivation: max PE over
HCal rec hits with `time < 50` ns, skipping BACK-section hits with
`minPE < 1`. Copy the loop verbatim. A different definition would break the
closure test in step C and the comparison with the talk.

### Pass names
Same as `cfg_ana_cutBasedDM_v492_nopnet.py`: veto, MIP and preselection from
pass `reco`, trigger from pass `sim`, recoil tracks `RecoilTracksClean`.

### Size control
51.6M ECal PN rows is fine as compressed floats (order 1 to 2 GB), so **store
every event, no prefilter**. A prefilter would cap how far the optimizer can
loosen a cut and would need separate denominator bookkeeping. Not worth it.

### Config
`cfg_ntuple_cnc.py`, modeled on `cfg_ana_cutBasedDM_v492_nopnet.py`: no
ParticleNet in the sequence, output to `./ntuple_cnc/<sample>/`, histogram file
named after the last input file as usual.

---

## 4. Step B: produce the ntuples

1. Unit test on one ECal PN file and one 1 MeV signal file, serially. This also
   compiles `libCnCNtuple.so`. Check the tree has the expected entries and that
   no branch is constant.
2. Submit all eight samples with `submit_sdf_mt_input.py`, tags `cncnt_<sample>`,
   **20 files per task** for backgrounds (no ParticleNet, so ~3 min per task),
   1 per task for signal. Use `-s 5` between submissions.
3. Verify completeness with `find_missing_chunks.py --ana ntuple_cnc <sample> <f>`
   (it checks the file holds content, not just that it exists) and resubmit
   what is missing.
4. Do not hadd the trees; read them with `ROOT.RDataFrame` over a glob, or
   `uproot`, which avoids a multi-GB merge.

Estimated: about 20 CPU-hours, so 15 to 30 minutes wall depending on the queue.

---

## 5. Step C: closure test (do not skip)

Before optimizing anything, apply the **current v14 thresholds** to the ntuple
and reproduce the talk's cut-and-count table at 1.5e14 EoT:

| | must reproduce |
| --- | --- |
| ECal PN after HCal | 59 |
| ECal conv. after HCal | < 1 |
| signal efficiency | 68.3 / 71.4 / 72.2 / 65.0 % |

Any mismatch means the ntuple definition differs from `CutBasedDM` and every
number downstream would be wrong. Fix it before continuing.

---

## 6. Step D: the optimization (`optimize_cnc_punzi.py`)

### Figure of merit
Punzi: `FOM = eps_S / (a/2 + sqrt(B))`

- `eps_S`: signal efficiency in the talk convention,
  `trig_eff * N(pass) / N(acceptance)`, with trig_eff = 0.8641 / 0.8578 /
  0.8672 / 0.8648 for 1 / 10 / 100 / 1000 MeV
- `B`: total background at 1.5e14 EoT, summed over all four samples with
  weights ECal PN 1.0424, ECal conv. 0.1593, Target PN 0.150, Target conv. 0.150
  (recompute coverage from the directories rather than trusting these)
- `a = 2` as the default; also report `a = 3` and `a = 5` so the sensitivity to
  that choice is visible

Punzi needs only the signal **efficiency**, not a cross section, which is the
right property here: signal yield scales with epsilon squared and has no EoT.

### What is optimized
- The eight ECal thresholds and `N_straight`: optimized
- `HCal maxPE < 8`: **fixed** by default, because it is shared with the BDT and
  PNet chains and fixing it keeps the three-way comparison fair. Run once with it
  free as a separate result, clearly labelled
- **One common threshold set for all four masses**, maximizing the mean FOM over
  the masses, since a real analysis applies one selection. Report the per-mass
  optima alongside as a reference for how much is lost by sharing

### Search method
Thresholds are step functions, so gradient optimizers do not apply. Use
**coordinate ascent on a grid**:
1. seed from the v14 thresholds
2. for each cut in turn, scan ~60 values over its range with the others fixed,
   keep the FOM maximum
3. repeat full sweeps until no threshold moves (typically 3 to 6 sweeps)
4. repeat from ~20 random seeds inside the ranges and keep the best, to avoid
   a local optimum

Scan ranges: from the distribution minimum up to 2x the v14 value for each cut.

Cost: each evaluation is one boolean mask over the arrays, so a full run is a
few minutes on iana.

### Train/test split (essential)
After tight cuts only tens of ECal PN events survive. Optimizing and quoting on
the same events tunes the thresholds to those specific events and makes the
background look smaller than it is.

- **optimize** on even `eventNumber`, **quote** on odd, scaling the test-half
  yield by 2 (equivalently, each test event weighs ~2.08 for ECal PN)
- report train and test side by side; a large drop from test to train is the
  sign of over-tuning
- with half the sample one ECal PN event already weighs ~2.08, so **zero
  observed in the test half does not mean `< 1`**. Quote it as 0 observed with
  the 90% CL upper limit (2.3 events x 2.08 = ~4.8 at 1.5e14 EoT) rather than
  `< 1`

### The zero-ECal-hit population
11,917 ECal PN events have exactly zero ECal readout hits, and every
cut-and-count threshold is an upper bound, so they pass all eight ECal cuts for
free. The ParticleNet re-run will say how many of the 59 survivors are these
events (`CnCCutFlow_NHits`).

Run the optimization **twice**:
1. as the chain stands
2. with `nReadoutHits >= 1` required first

If the zero-hit events dominate, run 1 will spend its effort on a background
no threshold can remove, and only run 2 is meaningful. Do not silently adopt the
extra cut: report both, since it is a new selection requirement and the BDT
chain would need the same treatment for a fair comparison.

---

## 7. Coordination with the ParticleNet campaign

Any driver whose drain loop does `squeue -u tamasvami` will wait for **both**
campaigns' jobs. The CnC ntuple jobs are short, so the worst case is a delay of
under an hour, not a failure. Still, filter by job-name prefix in any new drain
loop (`squeue -u tamasvami -h -o '%j' | grep -c '^cnc_'`).

The ParticleNet side will not delete or rewrite anything under `ntuple_cnc/`, and
this plan must not touch `analysis/`, `analysis_pnetv11/` or `analysis_nhits/`.

---

## 8. Deliverables

| file | content |
| --- | --- |
| `scan_out/cnc_punzi_thresholds.txt` | optimized thresholds, both runs (with and without the hit requirement), a = 2, 3, 5 |
| `scan_out/cnc_punzi_table.tex` | full cutflow at the new thresholds, same layout as the talk's cut-and-count table, test half |
| `scan_out/cnc_punzi_train_vs_test.txt` | train vs test yields and efficiencies, the over-tuning check |
| `plots_pnet/cnc_punzi_fom.pdf` | FOM per sweep, to show convergence |
| `plots_pnet/cnc_punzi_nminus1.pdf` | N-1 distributions at the optimized point, each with its new threshold |

Plots should follow `presentation_cnc_pnet_v15/PLOT_RESTYLE_PLAN.md` once its
color question is settled.

---

## 9. What to report back

1. Closure test result (step C), pass or fail
2. Old and new thresholds side by side
3. Background and signal efficiency at the new point, test half, both runs
4. Train vs test, so over-tuning is visible
5. Which cuts moved the most and which were found to do nothing. The variable
   plots already suggest `E_cell,max` and shower RMS separate weakly, so expect
   the optimizer to loosen those
