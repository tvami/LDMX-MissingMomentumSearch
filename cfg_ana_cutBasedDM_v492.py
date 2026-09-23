"""Cutflow histogramming over the v4.9.2 reco_v492 files.

Those files already carry the Humberto BDT in EcalVeto_reco, so the veto is read
straight from the reco pass instead of being re-run.
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
outputDir = './analysis/' + os.path.dirname(rel)
os.makedirs(outputDir, exist_ok=True)
# one output per chunk, named after the last input in it (framework convention)
p.histogram_file = outputDir + "/" + os.path.basename(fileName.split(' ')[-1])[:-5] + '_histo.root'
print("Histogram output = ", p.histogram_file)

# the original config had "signal = False" in both branches, so the analyzer
# never read RecoilTruthFiducialFlags and the Acceptance histogram stayed empty
signal = "signal" in fileName

# matches EcalVetoProcessor.disc_cut on iss2142-humberto_bdt
BDT_CUT = 0.954651

# ParticleNet costs ~65 ms/event, which dominates everything else. Only the
# ParticleNet table needs it, and that table has a single background column
# (ECal PN), so run it selectively. With RUN_PNET=0 the PNet cutflow is simply
# left empty; every other cutflow is unaffected.
RUN_PNET = os.environ.get('RUN_PNET', '1') != '0'

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
    pnet_pass_name='analysis' if RUN_PNET else '',
    pnet_cut=0.74,
    bdt_cut=BDT_CUT,
    bdt_loose_cut=0.9,
)

p.log_frequency = 1000
if RUN_PNET:
    # ParticleNet was dropped from the slim reco, so re-run it here
    pnetVeto = EcalPnetVetoProcessor(
        ecal_rec_hits_passname='sim',
        ecal_sp_hits_passname='sim',
        track_pass_name='reco',
    )
    p.sequence = [pnetVeto, cutBasedAna]
else:
    p.sequence = [cutBasedAna]
