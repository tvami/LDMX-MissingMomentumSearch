"""Cutflow histogramming for the GENIE target-EN sample.

The existing v4.8.1 EN reco is READABLE by v4.9.2 (the Track/TrackState schema
break is between v4.5.x and v4.8.1, not after), so no re-reco is needed. The
stored EcalVeto is the old segmip BDT though, so the veto is re-run here with
the Humberto BDT and lands in the 'analysis' pass.

EN-specific pass names: sim collections are 'test', reco is 'reco', and the
sample has no EcalPreselectionDecision at all so the skimmer runs here too.
"""
import os
import sys

from LDMX.Framework import ldmxcfg
p = ldmxcfg.Process('analysis')

import LDMX.Ecal.ecal_hardcoded_conditions
import LDMX.Ecal.ecal_geometry
from LDMX.Ecal.vetos import EcalVetoProcessor, EcalMipProcessor
from LDMX.Recon.ecal_preselection_skimmer import EcalPreselectionSkimmer

p.max_events = -1
p.skip_corrupted_input_files = True

with open(sys.argv[1]) as f:
    fileIn = f.read().split()
fileName = " ".join(fileIn)

p.input_files = fileIn
print("Input files = ", p.input_files)

outputDir = './analysis/' + str(fileIn[0].split('/')[-2])
os.makedirs(outputDir, exist_ok=True)
p.histogram_file = outputDir + "/" + os.path.basename(fileName.split(' ')[-1])[:-5] + '_histo.root'
print("Histogram output = ", p.histogram_file)

BDT_CUT = 0.954651

ecalVeto = EcalVetoProcessor(
    rec_pass_name='reco',
    sp_pass_name='test',
    sim_particles_passname='test',
    track_pass_name='reco',
)
ecalMip = EcalMipProcessor(
    ecal_pass_name='analysis',   # the veto we just re-ran
    mip_pass_name='analysis',    # EcalTrajectoryInfo it writes
)
presel = EcalPreselectionSkimmer(
    instance_name='ecalPreselectionSkimmer',
    ecal_rec_hit_pass='reco',
)

cutBasedAna = ldmxcfg.processor_from_file(
    'CutBasedDM.cxx',
    needs=['Ecal_Event', 'Hcal_Event', 'Recon_Event', 'SimCore_Event', 'Tracking_Event'],
    fiducial_analysis=True,
    trigger_pass='reco',
    sp_pass_name='test',
    signal=False,
    ignore_fiducial_analysis=True,
    recoil_track_collection='RecoilTracksClean',
    ecal_veto_pass_name='analysis',
    ecal_mip_pass_name='analysis',
    preselection_pass_name='analysis',
    bdt_cut=BDT_CUT,
    bdt_loose_cut=0.9,
)

p.log_frequency = 1000
p.sequence = [ecalVeto, ecalMip, presel, cutBasedAna]
