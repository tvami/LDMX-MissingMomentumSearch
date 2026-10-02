"""Cutflow histogramming with the v11 ParticleNet (iss2168-pnet-update).

Same as cfg_ana_cutBasedDM_v492.py, except ParticleNet always runs and the
output goes to analysis_pnetv11/ so the v10 results stay where they are.

The PNet cut is NOT passed to the analyzer any more. v11 cuts on the logit
difference because the probability saturates at 1 in float, and that difference
is not stored in EcalVetoResult, so the analyzer has to take passesVeto() from
the processor. The one place the cut is defined is EcalPnetVetoProcessor.
"""
import os
import sys

from LDMX.Framework import ldmxcfg
p = ldmxcfg.Process('analysis')

import LDMX.Ecal.ecal_hardcoded_conditions
import LDMX.Ecal.ecal_geometry
from LDMX.Ecal.vetos import EcalPnetVetoProcessor

p.max_events = -1
p.skip_corrupted_input_files = True

with open(sys.argv[1]) as f:
    fileIn = f.read().split()
fileName = " ".join(fileIn)

p.input_files = fileIn
print("Input files = ", p.input_files)

# mirror the reco_v492 tree so signal keeps <sample>/<mass>/ rather than a bare "1.0"
rel = fileIn[0].split('/reco_v492/')[-1]
outputDir = './analysis_pnetv11/' + os.path.dirname(rel)
os.makedirs(outputDir, exist_ok=True)
# one output per chunk, named after the last input in it (framework convention)
p.histogram_file = outputDir + "/" + os.path.basename(fileName.split(' ')[-1])[:-5] + '_histo.root'
print("Histogram output = ", p.histogram_file)

signal = "signal" in fileName

# matches EcalVetoProcessor.disc_cut on iss2142-humberto_bdt
BDT_CUT = 0.954651

cutBasedAna = ldmxcfg.processor_from_file(
    'CutBasedDM.cxx',
    needs=['Ecal_Event', 'Hcal_Event', 'Recon_Event', 'SimCore_Event', 'Tracking_Event'],
    fiducial_analysis=True,
    trigger_pass="sim",
    signal=signal,
    # no ECal-fiducial cut anywhere: the table's acceptance row is the truth
    # acceptance (signal) and 100% for backgrounds, so bin 1 must pass all
    ignore_fiducial_analysis=True,
    recoil_track_collection='RecoilTracksClean',
    ecal_veto_pass_name='reco',
    ecal_mip_pass_name='reco',
    preselection_pass_name='reco',
    pnet_pass_name='analysis',
    bdt_cut=BDT_CUT,
    bdt_loose_cut=0.9,
)

p.log_frequency = 1000
# ParticleNet was dropped from the slim reco, so re-run it here. Model and cut
# come from the vetos.py defaults: particle_net_ecal_v11, disc_cut 0.5664.
pnetVeto = EcalPnetVetoProcessor(
    ecal_rec_hits_passname='sim',
    track_pass_name='reco',
)
p.sequence = [pnetVeto, cutBasedAna]
