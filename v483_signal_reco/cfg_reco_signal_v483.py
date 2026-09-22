"""Re-run the reco step on Jihoon's signal sim, in v4.8.3.

Input : /home/jihoonyoo/LDMX/8GeV_Samples/v15_plot400/sig_reco/*_pres_reco_v1.root
Output: /home/vamitamas/Samples8GeV/sig_reco_dropsim_v483_<bdt>/<mass>/*_reco.root

Those files carry a complete sim record (Ecal/Hcal/Tagger/Recoil/Target sim
hits plus every scoring plane) alongside an old reco pass named 'reco_v1', so
the whole reco can be redone from the sim hits.

The stale 'reco_v1' pass cannot be removed with ldmx-sw's ignore/drop rules:
EventFile.cxx reactivates "*" after cloning, so ROOT still deserialises
v4.5.11's Track::TrackState, which does not read back under v4.8.3. It is
removed beforehand by strip_signal.py instead -- except for four split
single-object products (EcalVeto/HcalVeto/TrackerVeto/EcalTrajectoryInfo) that
ROOT refuses to drop, so their consumers are pinned to this pass by name below.

Unlike the v4.5.11 signal production this one produces EcalMipInfo and
RecoilTruthFiducialFlags, so the analysis regains the MIP veto and a real
truth-fiducial acceptance denominator.
"""

import os
import re
import sys

from LDMX.Framework import ldmxcfg

p = ldmxcfg.Process("reco")

# ---------------------------------------------------------------- input files
arg = sys.argv[1]
if arg.endswith(".root"):
    fileIn = [arg]
else:
    with open(arg) as f:
        fileIn = f.read().split()
fileName = " ".join(fileIn)

p.max_events = -1
p.input_files = fileIn
p.skip_corrupted_input_files = True
print("Input files = ", p.input_files)

BDT = os.environ.get("LDMX_BDT", "segmip")

match = re.search(r"signal_mass_([0-9]+MeV)", fileName.split("/")[-1])
massTag = match.group(1) if match else "unknown_mass"

outputDir = "/home/vamitamas/Samples8GeV/sig_reco_dropsim_v483_%s/%s" % (BDT, massTag)
os.makedirs(outputDir, exist_ok=True)
p.output_files = [outputDir + "/" + str(fileName.split("/")[-1][:-5]) + "_reco.root"]
print("Output file = ", p.output_files)

p.log_frequency = 1000

# ------------------------------------------------------------------- geometry
import LDMX.Ecal.ecal_geometry  # noqa: F401,E402
import LDMX.Ecal.ecal_hardcoded_conditions  # noqa: F401,E402
import LDMX.Hcal.hcal_geometry  # noqa: F401,E402
import LDMX.Hcal.hcal_hardcoded_conditions  # noqa: F401,E402

from LDMX.Tracking import full_tracking_sequence  # noqa: E402
from LDMX.Ecal import vetos as ecal_vetos  # noqa: E402
from LDMX.Ecal import ecal_clusters  # noqa: E402
from LDMX.Hcal import digi as hcal_digi  # noqa: E402
from LDMX.Hcal import hcal  # noqa: E402
from LDMX.Recon.fiducial_flag import RecoilFiducialityProcessor  # noqa: E402
from LDMX.TrigScint import trig_scint  # noqa: E402

# --------------------------------------------------------------- ECal BDT here
ecal_veto = ecal_vetos.EcalVetoProcessor()
if BDT == "helena":
    ecal_veto.bdt_file = "/home/vamitamas/LDMX-CutBasedDM/helena.onnx"
    ecal_veto.bdt_feature_config = "helena"

ecal_mip = ecal_vetos.EcalMipProcessor()
# Jihoon's files still carry EcalVeto/HcalVeto/TrackerVeto/EcalTrajectoryInfo
# from the old 'reco_v1' pass -- ROOT will not let those branches be stripped
# -- so every consumer that would otherwise look them up with an empty pass
# name has to be pinned to this process, or the lookup is ambiguous.
ecal_mip.ecal_pass_name = "reco"
ecal_mip.mip_pass_name = "reco"
ecal_veto_pnet = ecal_vetos.EcalPnetVetoProcessor()
ecal_veto_pnet.track_pass_name = "reco"

hcal_veto = hcal.HcalVetoProcessor()
hcal_veto.track_pass_name = "reco"

ts_digis = [
    trig_scint.TrigScintDigiProducer.pad1(),
    trig_scint.TrigScintDigiProducer.pad2(),
    trig_scint.TrigScintDigiProducer.pad3(),
]
ts_clusters = [
    trig_scint.TrigScintClusterProducer.pad1(),
    trig_scint.TrigScintClusterProducer.pad2(),
    trig_scint.TrigScintClusterProducer.pad3(),
]

p.sequence = []
p.sequence.extend(full_tracking_sequence.sequence)
p.sequence.extend(
    [
        RecoilFiducialityProcessor(),
        ecal_clusters.EcalClusterProducer(),
        ecal_veto,
        ecal_mip,
        ecal_veto_pnet,
        hcal_digi.HcalDigiProducer(),
        hcal_digi.HcalRecProducer(),
        hcal_veto,
        *ts_digis,
        *ts_clusters,
        trig_scint.trig_scint_track,
    ]
)

# ------------------------------------------------------------------ I/O rules
# The stale 'reco_v1' pass and the unused sim collections were already removed
# by strip_signal.py, which had to be done outside ldmx-sw: EventFile.cxx
# pushes reactivate_rules_ "*" after cloning, so an 'ignore' rule still lets
# ROOT deserialise the branch, and v4.5.11's Track::TrackState does not read
# back under v4.8.3 dictionaries.
#
# What remains is only what the reco consumes, so the sim hits just need
# dropping from the output to match the background reco_dropsim content.
p.keep = [
    "drop .*SimHits.*",
]
