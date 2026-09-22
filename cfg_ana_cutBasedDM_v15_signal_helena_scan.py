"""Signal analysis with the ECal veto re-scored using helena.onnx.

Jihoon's signal reco carries an EcalVeto in the pass 'reco_v1' scored with the
stock segmip BDT (verified: re-scoring with segmip reproduces the stored disc
exactly, max|diff| = 0). Here EcalVetoProcessor is re-run in this process with
helena.onnx and the analyzer reads THAT one, via ecal_veto_pass_name - the same
trick as cfg_ana_cutBasedDM_v15_helena.py does for the background.

Signal-specific differences from the background helena config:
  - the reco products live in the pass 'reco_v1', not 'reco'
  - EcalPreselectionDecision lives in the pass 'Skim', not 'ecal_pres'
  - output directory is per A' mass point

disc_cut is still segmip's working point (0.99741); helena has no tuned
operating point, so the score itself is what matters, and it is stored in the
BDTDiscr histograms.

Output: ./analysis_signal_helena/<mass>/<file>_histo.root
"""

import os
import re
import sys

from LDMX.Framework import ldmxcfg

p = ldmxcfg.Process('analysis')

import LDMX.Ecal.ecal_hardcoded_conditions  # noqa: F401,E402
from LDMX.Ecal import EcalGeometry  # noqa: F401,E402
from LDMX.Ecal import vetos  # noqa: E402

p.maxEvents = -1
p.skipCorruptedInputFiles = True

arg = sys.argv[1]
if arg.endswith('.root'):
    fileIn = [arg]
else:
    with open(arg) as f:
        fileIn = f.read().split()
fileName = " ".join(fileIn)

p.inputFiles = fileIn
print("Input files = ", p.inputFiles)

match = re.search(r'signal_mass_([0-9]+MeV)', fileName.split('/')[-1])
massTag = match.group(1) if match else 'unknown_mass'

outputDir = './analysis_signal_helena_scan/' + massTag
os.makedirs(outputDir, exist_ok=True)
p.histogramFile = outputDir + "/" + str(fileName.split('/')[-1][:-5]) + '_histo.root'
print("Histogram output = ", p.histogramFile)

# ---------------------------------------------------------------- Ecal veto
ecalVeto = vetos.EcalVetoProcessor()
ecalVeto.bdt_file = '/home/vamitamas/LDMX-CutBasedDM/helena.onnx'
ecalVeto.bdt_feature_set = 'helena'
ecalVeto.recoil_from_tracking = True
ecalVeto.track_collection = 'RecoilTracksClean'
ecalVeto.track_pass_name = 'reco_v1'
ecalVeto.rec_pass_name = ''
ecalVeto.sim_particles_passname = 'sim'

# ------------------------------------------------------------------ Analyzer
cutBasedAna = ldmxcfg.Analyzer.from_file(
    'CutBasedDM.cxx',
    needs=['Ecal_Event', 'Hcal_Event', 'Recon_Event', 'SimCore_Event', 'Tracking_Event'])
cutBasedAna.fiducial_analysis = True
cutBasedAna.ignore_fiducial_analysis = False
cutBasedAna.trigger_pass = "sim"
# RecoilTruthFiducialFlags is absent from these files, and the signal branch is
# the only thing that reads it.
cutBasedAna.signal = False
cutBasedAna.recoil_track_collection = 'RecoilTracksClean'
# read the EcalVeto produced above in THIS process, not the one from 'reco_v1'
cutBasedAna.ecal_veto_pass_name = 'analysis'
cutBasedAna.preselection_pass_name = 'Skim'

p.sequence = []
p.termLogLevel = 10
p.logFrequency = 1000
p.sequence.extend([ecalVeto, cutBasedAna])
