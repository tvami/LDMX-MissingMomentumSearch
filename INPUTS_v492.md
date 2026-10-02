# v15 cutflow study inputs (ldmx-sw v4.9.2, Humberto BDT)

Where every file that feeds the v15 tables and plots lives, and how to remake it.

Workspace: `/sdf/group/ldmx/users/tamasvami/ldmx-analysis/v4.9.2/ldmx-sw`
ldmx-sw branch: `iss2142-humberto_bdt` (BDT disc cut 0.954651)
All paths below are relative to this repo unless they start with `/sdf`.

## 1. Histogram files

Everything is under `analysis/`.

### Hadded per sample, one file per column

These are what `make_final_table.py`, `dump_cnc_pnet.py` and the overlay script
actually open.

| file | chunks merged |
| --- | --- |
| `analysis/ecal_pn_v15_8gev_histos.root` | 297 |
| `analysis/ecal_conversion_v15_8gev_histos.root` | 47 |
| `analysis/target_pn_v15_8gev_histos.root` | 3 |
| `analysis/target_conversion_v15_8gev_histos.root` | 9 |
| `analysis/signal_v15_8gev_0.001_histos.root` | 30 |
| `analysis/signal_v15_8gev_0.01_histos.root` | 30 |
| `analysis/signal_v15_8gev_0.1_histos.root` | 30 |
| `analysis/signal_v15_8gev_1.0_histos.root` | 30 |
| `analysis/signal_mass_1MeV_v15_8GeV_histos.root` | copy of `0.001` |
| `analysis/signal_mass_10MeV_v15_8GeV_histos.root` | copy of `0.01` |
| `analysis/signal_mass_100MeV_v15_8GeV_histos.root` | copy of `0.1` |
| `analysis/signal_mass_1000MeV_v15_8GeV_histos.root` | copy of `1.0` |

Each signal mass exists under two names on purpose: `make_final_table.py` keys
off the eps value, while `compareWithArguementList2D.py` builds its legend from
`1MeV`/`10MeV`/... substrings of the filename. `hadd_v492.sh` writes the eps
form and copies it to the mass form.

Every file is 0.1 to 0.2 MB, all written 2026-09-28 13:58. The whole
`analysis/` tree is 66 MB.

### Per chunk, before hadd

| directory | files | files per chunk |
| --- | --- | --- |
| `analysis/ecal_pn_v15_8gev/` | 297 | 20 |
| `analysis/ecal_conversion_v15_8gev/` | 47 | 20 |
| `analysis/target_conversion_v15_8gev/` | 9 | 20 |
| `analysis/target_pn_v15_8gev/` | 3 | 20 |
| `analysis/signal_v15_8gev/{1.0,0.1,0.01,0.001}/` | 30 each | 1 |

A chunk histogram is named after the **last** reco file in the chunk, which is
what makes `find_missing_chunks.py` able to name exactly which chunks are
missing instead of rerunning a whole sample.

Do not mix chunk sizes within one sample. A 5 file chunk ending at `files[19]`
writes the same histogram name as the 20 file chunk covering `files[0:20]`, so
it overwrites it and silently drops 15 files.

`analysis/tmp/<stem>.list` holds the exact input list of each hadd, and
`analysis/tmp/<stem>.err` its stderr. Useful for checking after the fact which
chunks went into a merge.

## 2. Reco inputs the histograms were filled from

`/sdf/data/ldmx/private_production/mc26/reco_v492/<sample>/*_reco.root`, 2.1 TB.
Reachable only from `sdfiana006`/`sdfiana007`.

| sample | reco files | pres_skim files | coverage |
| --- | --- | --- | --- |
| `target_pn_v15_8gev` | 46 | 46 | 1.000 |
| `target_conversion_v15_8gev` | 167 | 167 | 1.000 |
| `ecal_pn_v15_8gev` | 5921 | 6172 | 1.042 |
| `ecal_conversion_v15_8gev` | 933 | 991 | 1.062 |
| `signal_v15_8gev/{1.0,0.1,0.01,0.001}` | 30 each | 30 each | 1.000 |

This is a full re-reco of the mc26 preselection skim with v4.9.2, needed because
v4.9.2 cannot read the `Track` branches written by v4.5.x (the versionless
`TrackState` struct changed layout). The reco config is
`../cfg_reco_nosim_skim_v492.py`; sim collections are dropped.

Coverage is `pres_skim files / reco files` and corrects the yields for the reco
files that never came back. `make_final_table.py` computes it live, so it
tracks the directory rather than a hardcoded number.

The "conversion" samples are gamma to mu+mu- (`BiasOperator::GammaToMuPair`),
not deep PN. That is from the production `RunHeader`, not inferred from the name.

## 3. Normalization

All columns are scaled to a common **1.5e14 EoT (8 GeV)**.

Per sample EoT, the coverage correction, and the resulting weight of one
observed event. These are the `BKGS` and `SIGS` tables at the top of
`make_final_table.py`; the EoT values are the only hardcoded physics input in
the whole chain, so they are the first thing to check if a column looks off.

| sample | sample EoT | coverage | weight per event at 1.5e14 |
| --- | --- | --- | --- |
| Target PN | 1.0e15 | 1.000 | 0.150 |
| Target conv. | 1.0e15 | 1.000 | 0.150 |
| Target EN | 1.5e14 | none applied | 1.000 |
| ECal PN | 1.5e14 | 1.042 | 1.042 |
| ECal conv. | 1.0e15 | 1.062 | 0.159 |

Signal is generated at 1.5e14 EoT, weight 1.0, no coverage correction.

`make_final_table.py` prints the per event weight for every column, so a `<1`
claim in the table stays checkable: it is only honest when one observed event
weighs less than 1 after scaling. ECal PN is the one column where the weight
exceeds 1 (1.042 from the coverage correction), so a `<1` there would be
flagged `MISLEADING` rather than printed.

Two rows do not come from the cutflow histograms:

- **Triggered**: the four skimmed backgrounds are 100% trigger pass by
  construction, so their trigger row is counted from `mc26/trigger_skim` instead
  of a cutflow bin. The counts are hardcoded in `make_final_table.py`:
  Target PN 7.118e5, Target conv. 5.572e6, ECal PN 2.116e8, ECal conv. 8.046e7.
  EN is not trigger skimmed, so its trigger row is a real cutflow bin.
- **Acceptance**: 100% for backgrounds; for signal it is the truth acceptance
  from the `Acceptance` histogram (94.7 / 80.7 / 77.1 / 65.2% for
  1 / 10 / 100 / 1000 MeV).

### Raw counts behind the table

Straight out of the cutflow histograms, before any EoT scaling, as recorded in
the header comments of `../scan_out/final_table.tex`. Bin numbers are the `ROWS`
list: 2 triggered, 3 preselection skim, 4 tracker veto, 5 ECal veto,
6 `N_straight < 3`, 7 HCal maxPE < 8.

| sample | 2 | 3 | 4 | 5 | 6 | 7 |
| --- | --- | --- | --- | --- | --- | --- |
| Target PN | 383327 | 383327 | 57165 | 3269 | 3074 | 0 |
| Target conv. | 1817720 | 1817720 | 10421 | 0 | 0 | 0 |
| ECal PN | 51638108 | 51638108 | 46353583 | 145449 | 138083 | 1 |
| ECal conv. | 37251723 | 37251723 | 35319665 | 2 | 2 | 2 |

Bins 2 and 3 are equal for every background because these samples are already
preselection skimmed, so nothing is lost at that step by construction.

Measured trigger efficiencies, from fresh unskimmed sims via `cfg_trigeff.py`
plus `TrigEffAna.cxx`: ECal PN 8.13%, ECal conv. 76.1%, Target conv. 75.6%,
Target PN 23.6%, Target EN 0.153%, signal about 86% and flat in mass.

## 4. Cutflow histograms inside each file

All in the `CutBasedDM` directory of the ROOT file.

| histogram | bins | used for |
| --- | --- | --- |
| `StdCutFlowWithTracking_RecoilX` | 8 | the main BDT cutflow table |
| `CnCCutFlow_RecoilX` | 11 | cut and count table |
| `PNetCutFlow_RecoilX` | 5 | ParticleNet table |
| `Acceptance` | | signal truth acceptance |

The analyzer is `CutBasedDM.cxx` (v26). Note the track momentum port: v4.9.2
`getMomentumAtTarget()` returns MeV in the LDMX frame with the beam along z, so
the transverse momentum is `sqrt(p[0]^2 + p[1]^2)`, not the old
`1000*sqrt(p[1]^2 + p[2]^2)`.

## 5. Configs and scripts

| file | role |
| --- | --- |
| `../cfg_reco_nosim_skim_v492.py` | re-reco of pres_skim into `reco_v492`, sim dropped |
| `cfg_ana_cutBasedDM_v492.py` | histogramming, ParticleNet on |
| `cfg_ana_cutBasedDM_v492_nopnet.py` | same, ParticleNet off |
| `cfg_ana_cutBasedDM_en.py` | EN, runs over v4.8.1 reco directly |
| `find_missing_chunks.py` | which chunks have no usable histogram, writes one filelist each |
| `prune_strays.py` | deletes histograms that are not the expected output of a chunk |
| `hadd_v492.sh` | per chunk to per sample merge, two stage above 400 inputs |
| `make_final_table.py` | the final table at 1.5e14 EoT |
| `dump_cnc_pnet.py`, `make_cnc_pnet_tables.py` | cut and count and ParticleNet tables |
| `chk_cnc.py` | sanity check on the cut and count bins |
| `compareWithArguementList2D.py` | the overlay plots |
| `Histos_v492.txt` | the 9 line input list the overlay script reads |

A separate ParticleNet config exists because `denv` does not copy environment
variables into the container (`denv_env_var_copy_all="false"`), so a `RUN_PNET`
env var never reached the job. ParticleNet costs about 65 ms per event, which is
why it is off for the samples that only feed the cut and count table.

`find_missing_chunks.py` checks that a histogram file actually holds
histograms, not just that it exists and is nonempty. A killed job leaves a file
of about 500 bytes with no keys, because histograms are only written at close.

## 6. Plots

Output: `CompareHistos_v492/<variable>_analysis/`, one PNG per sample plus the
overlays. The four proceeding plots are swapped into
`/sdf/group/ldmx/users/tamasvami/ldmx-analysis/BSM25_proceeding_v15/` under
their original `CutBasedDM_*.png` filenames, with the v14 versions kept in
`v14_original/`.

## 7. Known gaps

### ECal PN zero-hit production defect (found 2026-10-01)

11,925 ECal PN events have **zero ECal readout hits**. They are a defect in the
original production, not physics, and they dominate the cut-and-count and
ParticleNet backgrounds.

- **24 reco files** hold 11,877 of them (99.6%), 218,077 events in total, 0.42%
  of the sample. The full list with per-file counts is
  `../scan_out/zerohit_files.txt`
- the affected simulation runs are in the range **240,560 to 248,772**, 55 to 89%
  of their events empty; 1,287 further events carry run number **-1**
- the defect is **upstream of the v4.9.2 re-reco**: the same events already have
  empty `EcalRecHits_sim` in the original pres_skim file, while every one of them
  has non-empty `EcalSimHits_sim` (checked on run 241558 against run 241557)
- they make 43 of the 44 ParticleNet ECal PN survivors and 47 of the 57
  cut-and-count survivors; the BDT chain rejects them on its own

**Fix: at least one ECal readout hit is required in every flow** (decided
2026-10-01). In `CutBasedDM.cxx` this is `has_ecal_readout_hit`, folded into the
BDT preselection row, the cut-and-count `N_hits` row and the ParticleNet loose
preselection. The histograms in `analysis/`, `analysis_pnetv11/` and
`analysis_nhits/` predate the change; tables with it applied were derived exactly
from the N_hits histograms by `make_tables_withhit.py` into
`../scan_out/tables_withhit.tex`. Result at 1.5e14 EoT: BDT 1, cut and count 10,
ParticleNet 1 ECal PN event, signal efficiencies unchanged. Scripts: `chk_zerohit.py`,
`chk_zerohit_clustering.py`, `chk_zerohit_runs.py`, `chk_zerohit_files.py`,
`chk_zerohit_source.py`.

### The three flows do not share their non-ECal cuts

In `CutBasedDM.cxx` the BDT flow applies the tracker veto and `N_straight < 3`,
the cut-and-count flow applies `N_straight < 3` only, and the ParticleNet flow
applies neither. The DR used the same three flows, so they are kept for DR
comparisons.

For a fair comparison between the three, `CnCAlignedCutFlow_RecoilX` and
`PNetAlignedCutFlow_RecoilX` apply trigger, at least one ECal hit, tracker veto,
`N_straight < 3` and the HCal veto, exactly like the BDT flow, and differ only in
the ECal selection. All eight samples were re-run into `analysis_aligned/`
(config `cfg_ana_cutBasedDM_aligned.py`, driver `drive_aligned.sh`); tables and a
0.001-binned ParticleNet threshold scan are in `../scan_out/tables_aligned.tex`
from `make_tables_aligned.py`. At 1.5e14 EoT: BDT 1, ParticleNet 1, cut and count
9 ECal PN events; signal efficiency 65.7/68.3/70.9/59.3% (BDT),
74.3/73.1/73.1/59.8% (ParticleNet), 64.5/66.9/67.3/55.3% (cut and count).

### Other gaps

- `Histos_v492.txt` line 7 points at `analysis/target_en_G21_11b_v15_8gev_histos.root`
  and `make_final_table.py` wants
  `analysis/targetEN_GENIE_G21_11b_00_000_v15_ti_8gev_histos.root`. Neither is
  on disk now and `hadd_v492.sh` builds neither. The EN plots in
  `CompareHistos_v492/` exist, so the file was there when the overlays ran and
  has since gone. The raw dump in `../scan_out/final_table.tex` confirms it:
  it has a raw counts line for all four other backgrounds and none for EN, so
  rerunning `make_final_table.py` as it stands now would give an empty EN
  column while the tex still carries the EN numbers from the earlier run.
  The EN histogramming would have to be rerun with
  `cfg_ana_cutBasedDM_en.py` over
  `/sdf/data/ldmx/private_production/mc26/reco_dropsim/targetEN_GENIE_G21_11b_00_000_v15_ti_8gev/`
  before either script can be rerun end to end. EN reco was not redone with
  v4.9.2, the v4.8.1 reco is readable as is.
- `reco_v492` still has its original name, a rename to `reco_v492_dropsim` was
  left as optional.
- The cut and count thresholds are the v14 values, not re-optimized for v15.

## 8. Operational notes

- Never write to home, the quota fills and jobs then die in one second with no
  log. SLURM jobs, logs and filelists go under
  `/sdf/group/ldmx/users/tamasvami/slurm/`.
- `denv` does not mount `/sdf/group/.../slurm` by default. Add it with
  `denv config mounts`.
- Compile `libCutBasedDM.so` once serially before submitting. `processor_from_file`
  recompiles when the source is newer, and parallel tasks racing on that corrupt
  the library. Never run git operations on the source while jobs are live.
- `/sdf/data/ldmx` is only visible from `sdfiana006`/`sdfiana007`.
