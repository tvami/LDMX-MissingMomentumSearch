import os
import sys
#fileName = sys.argv[1]
fileIn = sys.argv[1:]
fileName =  " ".join(sys.argv[1:])

from LDMX.Framework import ldmxcfg
p = ldmxcfg.Process('analysis')

import LDMX.Ecal.ecal_hardcoded_conditions
from LDMX.Ecal import EcalGeometry

p.maxEvents = -1
p.skipCorruptedInputFiles = True

with open(sys.argv[1]) as f:
    fileIn = f.read().split()
fileName = " ".join(fileIn)

p.inputFiles  = fileIn
print("Input files = ", p.inputFiles)

outputDir = f'./analysis/' + str(fileName.split('/')[-2])
os.makedirs(outputDir, exist_ok=True)
print("Output file = ", p.outputFiles)
p.histogramFile = outputDir + "/" + str(fileName.split('/')[-1][:-5]) + '_histo.root'
print("Histogram output = ", p.histogramFile)

# Local testing
# p.inputFiles = [f'/sdf/data/ldmx/private_production/reco_dropsim/ecal_pn_v15_8gev/v4.5.4_ecal_pn_run75746_event_sim_pres_reco.root']
# print("Input files = ", p.inputFiles)
# # p.histogramFile = fileName[:-5] + "_histot"
# #p.histogramFile = "/sdf/group/ldmx/users/tamasvami/CutBasedDM/"  + str(fileName.split('/')[-2]) + "/" + str(fileName.split('/')[-1][:-5]) + "_histo_v16.root"
# p.histogramFile  = str(fileName.split('/')[-1][:-5]) + "_histo_v17.root"
# print("Histogram output = ", p.histogramFile)

signal = False
if "signal" in fileName :
    signal = False


cutBasedAna = ldmxcfg.Analyzer.from_file('CutBasedDM.cxx', needs=['Ecal_Event','Hcal_Event','Recon_Event','SimCore_Event','Tracking_Event'])
#cutBasedAna.fiducial_analysis = False
cutBasedAna.fiducial_analysis = True
cutBasedAna.trigger_pass = "sim"
cutBasedAna.signal = signal
cutBasedAna.ignore_fiducial_analysis = False
# cutBasedAna.sp_pass_name = sp_pass_temp
cutBasedAna.recoil_track_collection = 'RecoilTracksClean'

p.sequence = []
p.termLogLevel = 10
p.logFrequency = 1000
p.sequence.extend([cutBasedAna])

