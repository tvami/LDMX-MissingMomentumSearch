"""cfg_ana_cutBasedDM_v15.py, but re-running the ECal veto with helena.onnx.

The reco_dropsim inputs already carry an EcalVeto from the 'reco' pass, scored
with the default segmip BDT. Here we re-run EcalVetoProcessor in this process
with helena.onnx and let the analyzer read THAT one, via the new
ecal_veto_pass_name parameter (reading 'EcalVeto' with an empty pass name would
now be ambiguous, since two passes provide it).

helena.onnx declares input [?, 44] while the stock buildBDTFeatureVector emits
47, so ldmx-sw is run with bdt_feature_set = 'helena' (added in the v4.5.11
tree): MIP-tracking placeholders dropped, n_tracking_hits added after ep_dot,
matching LDMX-scripts PR #124 bdtMaker.py.

Everything else - the tracks, the HCal/tracker vetoes, the MIP result, the
preselection decision - is still read from the input 'reco' pass, exactly as in
cfg_ana_cutBasedDM_v15.py.
"""
import os
import sys

from LDMX.Framework import ldmxcfg
p = ldmxcfg.Process('analysis')

import LDMX.Ecal.ecal_hardcoded_conditions
from LDMX.Ecal import EcalGeometry
from LDMX.Ecal import vetos

p.maxEvents = -1
p.skipCorruptedInputFiles = True

with open(sys.argv[1]) as f:
    fileIn = f.read().split()
fileName = " ".join(fileIn)

p.inputFiles = fileIn
print("Input files = ", p.inputFiles)

outputDir = f'./analysis_helena_scan/' + str(fileName.split('/')[-2])
os.makedirs(outputDir, exist_ok=True)
p.histogramFile = outputDir + "/" + str(fileName.split('/')[-1][:-5]) + '_histo.root'
print("Histogram output = ", p.histogramFile)

signal = False

# ---------------------------------------------------------------- Ecal veto
ecalVeto = vetos.EcalVetoProcessor()
ecalVeto.bdt_file = '/home/vamitamas/LDMX-CutBasedDM/helena.onnx'
ecalVeto.bdt_feature_set = 'helena'
# recoil comes from the tracks already in the input file
ecalVeto.recoil_from_tracking = True
ecalVeto.track_collection = 'RecoilTracksClean'
ecalVeto.track_pass_name = 'reco'
ecalVeto.rec_pass_name = ''
ecalVeto.sim_particles_passname = 'sim'
# NOTE: disc_cut is still segmip's working point (0.99741). helena's own
# operating point has not been set - the BDT score is stored in the histograms
# (BDTDiscr) so a new cut can be chosen from the distribution afterwards.

# ------------------------------------------------------------------ Analyzer
cutBasedAna = ldmxcfg.Analyzer.from_file('CutBasedDM.cxx', needs=['Ecal_Event','Hcal_Event','Recon_Event','SimCore_Event','Tracking_Event'])
cutBasedAna.fiducial_analysis = True
cutBasedAna.trigger_pass = "sim"
cutBasedAna.signal = signal
cutBasedAna.ignore_fiducial_analysis = False
cutBasedAna.recoil_track_collection = 'RecoilTracksClean'
# read the EcalVeto produced above in THIS process, not the one from 'reco'
cutBasedAna.ecal_veto_pass_name = 'analysis'

p.sequence = []
p.termLogLevel = 10
p.logFrequency = 1000
p.sequence.extend([ecalVeto, cutBasedAna])
