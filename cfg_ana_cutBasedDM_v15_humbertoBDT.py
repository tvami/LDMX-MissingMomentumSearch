import os
import sys

from LDMX.Framework import ldmxcfg
p = ldmxcfg.Process('analysis')

import LDMX.Ecal.ecal_hardcoded_conditions
import LDMX.Ecal.ecal_geometry
from LDMX.Ecal.vetos import EcalVetoProcessor

p.max_events = -1
p.skip_corrupted_input_files = True

with open(sys.argv[1]) as f:
    fileIn = f.read().split()
fileName = " ".join(fileIn)

p.input_files = fileIn
print("Input files = ", p.input_files)

outputDir = f'./analysis/' + str(fileName.split('/')[-2])
os.makedirs(outputDir, exist_ok=True)
p.histogram_file = outputDir + "/" + str(fileName.split('/')[-1][:-5]) + '_histo.root'
print("Histogram output = ", p.histogram_file)

signal = False
if "signal" in fileName:
    signal = False

# Re-run the ECal veto so the Humberto BDT score is recomputed from the stored
# rec hits. The file already has EcalVeto_reco from the segmip BDT, so this one
# lands in the 'analysis' pass and the analyzer is pointed at it explicitly.
ecalVeto = EcalVetoProcessor(
    rec_pass_name='sim',
    sp_pass_name='sim',
    sim_particles_passname='sim',
    track_pass_name='reco',
)

cutBasedAna = ldmxcfg.processor_from_file(
    'CutBasedDM.cxx',
    needs=['Ecal_Event', 'Hcal_Event', 'Recon_Event', 'SimCore_Event', 'Tracking_Event'],
    fiducial_analysis=True,
    trigger_pass="sim",
    signal=signal,
    ignore_fiducial_analysis=False,
    recoil_track_collection='RecoilTracksClean',
    # new veto from this process, MIP tracking still from the reco pass
    ecal_veto_pass_name='analysis',
    ecal_mip_pass_name='reco',
    bdt_cut=ecalVeto.disc_cut,
    bdt_loose_cut=0.9,
)

p.log_frequency = 1000
p.sequence = [ecalVeto, cutBasedAna]
