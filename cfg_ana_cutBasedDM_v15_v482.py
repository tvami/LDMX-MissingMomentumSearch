"""cfg_ana_cutBasedDM_v15.py ported to the v4.8.2 API, run over the v4.8.2 reco.

Differences from cfg_ana_cutBasedDM_v15.py, all forced by v4.8.2:
  - snake_case Process fields (max_events, input_files, histogram_file, ...);
    v4.8.2 raises KeyError on an unknown attribute, so the old camelCase names
    would fail loudly rather than be silently ignored
  - LDMX.Ecal.EcalGeometry -> LDMX.Ecal.ecal_geometry
  - ldmxcfg.Analyzer.from_file(...) -> ldmxcfg.processor_from_file(...), with
    the processor parameters passed as kwargs and class_name given explicitly
    (it would otherwise default to the file stem 'CutBasedDM_v482')
  - CutBasedDM_v482.cxx instead of CutBasedDM.cxx (Track::getMomentum now needs
    a TrackStateType)

The EcalVeto in these inputs was already scored with the chosen BDT at reco
time, so nothing is re-run here.

Output: ./analysis_v482/<variant>_<sample>/<file>_histo.root
"""

import os
import sys

from LDMX.Framework import ldmxcfg

p = ldmxcfg.Process("analysis")

import LDMX.Ecal.ecal_hardcoded_conditions  # noqa: F401,E402
import LDMX.Ecal.ecal_geometry  # noqa: F401,E402

p.max_events = -1
p.skip_corrupted_input_files = True

with open(sys.argv[1]) as f:
    fileIn = f.read().split()
fileName = " ".join(fileIn)

p.input_files = fileIn
print("Input files = ", p.input_files)

# .../reco_dropsim_v482_<variant>/<sample>/<file>.root -> <variant>_<sample>
outputDir = (
    "./analysis_v482/"
    + str(fileName.split("/")[-3]).replace("reco_dropsim_v482_", "")
    + "_"
    + str(fileName.split("/")[-2])
)
os.makedirs(outputDir, exist_ok=True)
p.histogram_file = outputDir + "/" + str(fileName.split("/")[-1][:-5]) + "_histo.root"
print("Histogram output = ", p.histogram_file)

cutBasedAna = ldmxcfg.processor_from_file(
    "CutBasedDM_v482.cxx",
    class_name="CutBasedDM",
    needs=["Ecal_Event", "Hcal_Event", "Recon_Event", "SimCore_Event", "Tracking_Event"],
    fiducial_analysis=True,
    ignore_fiducial_analysis=False,
    trigger_pass="sim",
    signal=False,
    recoil_track_collection="RecoilTracksClean",
)

p.logger.term_level = 10
p.log_frequency = 1000
p.sequence = [cutBasedAna]
