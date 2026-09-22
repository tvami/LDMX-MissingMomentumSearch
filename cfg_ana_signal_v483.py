"""CutBasedDM over the v4.8.3 signal reco.

Input : /home/vamitamas/Samples8GeV/sig_reco_dropsim_v483_<bdt>/<mass>/*_reco.root
Output: ./analysis_signal_v483_<bdt>/<mass>/<file>_histo.root

Two things this gains over the v4.5.11 signal analysis, both because the v4.8.3
reco actually produces them:
  - EcalMipInfo exists, so the MIP veto is applied (it was silently skipped
    before, making the signal cutflow not like-for-like with the background)
  - RecoilTruthFiducialFlags exists, so signal=True works and the
    "All / Acceptance" bin is the truth-fiducial subset rather than all events

Pass names have to be pinned throughout: Jihoon's files carry four split
single-object products from the old 'reco_v1' pass (EcalVeto, HcalVeto,
TrackerVeto, EcalTrajectoryInfo) that ROOT will not let us strip, so they ride
along into the reco output and make an unqualified lookup ambiguous.
"""

import os
import re
import sys

from LDMX.Framework import ldmxcfg

p = ldmxcfg.Process("analysis")

import LDMX.Ecal.ecal_hardcoded_conditions  # noqa: F401,E402
import LDMX.Ecal.ecal_geometry  # noqa: F401,E402

p.max_events = -1
p.skip_corrupted_input_files = True

arg = sys.argv[1]
if arg.endswith(".root"):
    fileIn = [arg]
else:
    with open(arg) as f:
        fileIn = f.read().split()
fileName = " ".join(fileIn)

p.input_files = fileIn
print("Input files = ", p.input_files)

match = re.search(r"signal_mass_([0-9]+MeV)", fileName.split("/")[-1])
massTag = match.group(1) if match else "unknown_mass"

# segmip: reads the EcalVeto the reco already stored in pass "reco"
outputDir = "./analysis_signal_v483_segmip/%s" % massTag
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
    # RecoilTruthFiducialFlags is present in this reco, so the truth-fiducial
    # acceptance denominator is finally available
    signal=True,
    recoil_track_collection="RecoilTracksClean",
    # disambiguate against the leftover 'reco_v1' products
    ecal_veto_pass_name="reco",
    veto_pass_name="reco",
    preselection_pass_name="Skim",
)

p.logger.term_level = 10
p.log_frequency = 1000
p.sequence = [cutBasedAna]
