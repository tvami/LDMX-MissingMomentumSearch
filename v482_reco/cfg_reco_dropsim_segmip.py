"""Re-run the reco step in v4.8.2 with the segmip ECal BDT.

Input : the preselection skims, /home/vamitamas/Samples8GeV/pres_skim/<sample>/*_pres.root
Output: /home/vamitamas/Samples8GeV/reco_dropsim_v482_segmip/<sample>/*_pres_reco.root

argv[1] is a text file holding whitespace-separated input .root paths (one
filelist per parallel task), same convention as cfg_preselection_skim.py so
`just fire-parallel` works.

Reproduces the branch content of the existing reco_dropsim files:
  - the sim pass keeps SimParticles, the Ecal/Target/TrigScint scoring planes,
    EcalDigis, EcalRecHits and Trigger; every SimHits collection and the
    Hcal/Tracker/Magnet scoring planes are dropped (see p.keep below)
  - the ecal digi/rec and the trigger already exist in the sim pass and the
    preselection decision in the 'ecal_pres' pass, so none of them are re-run
  - the reco pass adds the full tracking sequence (incl. the tracker veto),
    the recoil fiduciality flags, ecal clusters/veto/mip/pnet, hcal
    digi/rec/veto and the trigger scintillator chain

The reco DQM is NOT run here (the old production wrote *_histo.root next to
the events); nothing downstream of this reads it and it costs time.
"""

import os
import sys

from LDMX.Framework import ldmxcfg

p = ldmxcfg.Process("reco")

# ---------------------------------------------------------------- input files
# argv[1] is either a single .root file (one fire invocation per input file,
# so a crash costs one file instead of a whole batch) or a text file listing
# whitespace-separated .root paths.
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

outputDir = "/home/vamitamas/Samples8GeV/reco_dropsim_v482_segmip/" + str(
    fileName.split("/")[-2]
)
os.makedirs(outputDir, exist_ok=True)
p.output_files = [
    outputDir + "/" + str(fileName.split("/")[-1][:-5]) + "_reco.root"
]
print("Output file = ", p.output_files)

p.log_frequency = 1000

# ------------------------------------------------------------------- geometry
import LDMX.Ecal.ecal_geometry  # noqa: F401
import LDMX.Ecal.ecal_hardcoded_conditions  # noqa: F401
import LDMX.Hcal.hcal_geometry  # noqa: F401
import LDMX.Hcal.hcal_hardcoded_conditions  # noqa: F401

from LDMX.Tracking import full_tracking_sequence
from LDMX.Ecal import vetos as ecal_vetos
from LDMX.Ecal import ecal_clusters
from LDMX.Hcal import digi as hcal_digi
from LDMX.Hcal import hcal
from LDMX.Recon.fiducial_flag import RecoilFiducialityProcessor
from LDMX.TrigScint import trig_scint

# --------------------------------------------------------------- ECal BDT here
ecal_veto = ecal_vetos.EcalVetoProcessor()  # bdt_feature_config defaults to segmip

ecal_mip = ecal_vetos.EcalMipProcessor()
ecal_veto_pnet = ecal_vetos.EcalPnetVetoProcessor()

hcal_veto = hcal.HcalVetoProcessor()

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

# ------------------------------------------------------------------ drop rules
# Match the existing reco_dropsim content: no SimHits, and only the Ecal /
# Target / TrigScint scoring planes survive.
p.keep = [
    "drop .*SimHits.*",
    "drop HcalScoringPlaneHits.*",
    "drop TrackerScoringPlaneHits.*",
    "drop MagnetScoringPlaneHits.*",
]
