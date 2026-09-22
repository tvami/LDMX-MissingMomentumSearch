"""cfg_ana_cutBasedDM_v15.py adapted to Jihoon's signal reco.

Differences from the background config, all forced by how those files were made
(/home/jihoonyoo/LDMX/8GeV_Samples/v15_plot400/sig_reco):
  - the reco products live in the pass 'reco_v1', not 'reco'
  - EcalPreselectionDecision lives in the pass 'Skim', not 'ecal_pres'
  - one output directory per A' mass point rather than per sample directory,
    since every mass sits in the same sig_reco/ directory

argv[1] is either a single .root file or a text file listing whitespace-
separated .root paths.

Output: ./analysis_signal/<mass>/<file>_histo.root
"""

import os
import re
import sys

from LDMX.Framework import ldmxcfg

p = ldmxcfg.Process('analysis')

import LDMX.Ecal.ecal_hardcoded_conditions  # noqa: F401,E402
from LDMX.Ecal import EcalGeometry  # noqa: F401,E402

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

# .../v4.5.4_signal_mass_1000MeV_v15_8GeV_1e_1_pres_reco_v1.root -> 1000MeV
match = re.search(r'signal_mass_([0-9]+MeV)', fileName.split('/')[-1])
massTag = match.group(1) if match else 'unknown_mass'

outputDir = './analysis_signal/' + massTag
os.makedirs(outputDir, exist_ok=True)
p.histogramFile = outputDir + "/" + str(fileName.split('/')[-1][:-5]) + '_histo.root'
print("Histogram output = ", p.histogramFile)

cutBasedAna = ldmxcfg.Analyzer.from_file(
    'CutBasedDM.cxx',
    needs=['Ecal_Event', 'Hcal_Event', 'Recon_Event', 'SimCore_Event', 'Tracking_Event'])
cutBasedAna.fiducial_analysis = True
cutBasedAna.ignore_fiducial_analysis = False
cutBasedAna.trigger_pass = "sim"
# RecoilTruthFiducialFlags is not in these files, and it is the only thing the
# signal branch reads, so the acceptance bin cannot be filled from truth here.
cutBasedAna.signal = False
cutBasedAna.recoil_track_collection = 'RecoilTracksClean'
cutBasedAna.ecal_veto_pass_name = 'reco_v1'
cutBasedAna.preselection_pass_name = 'Skim'

p.sequence = []
p.termLogLevel = 10
p.logFrequency = 1000
p.sequence.extend([cutBasedAna])
