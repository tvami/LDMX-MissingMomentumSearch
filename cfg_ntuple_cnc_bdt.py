"""Flat cut-and-count ntuple with the tracker veto and the BDT score.

Feeds optimize_cnc_punzi.py (PLAN_CNC_PUNZI.md). No ParticleNet, no
CutBasedDM: this job loads only libCnCNtuple.so.
"""
import os
import sys

from LDMX.Framework import ldmxcfg
p = ldmxcfg.Process('cncntuple')

p.max_events = -1
p.skip_corrupted_input_files = True

with open(sys.argv[1]) as f:
    fileIn = f.read().split()
fileName = " ".join(fileIn)

p.input_files = fileIn
print("Input files = ", p.input_files)

# mirror the reco_v492 tree, as in cfg_ana_cutBasedDM_v492_nopnet.py
rel = fileIn[0].split('/reco_v492/')[-1]
outputDir = './ntuple_cnc_bdt/' + os.path.dirname(rel)
os.makedirs(outputDir, exist_ok=True)
# named after the last input, so find_missing_chunks.py can match chunks
p.histogram_file = outputDir + "/" + os.path.basename(fileName.split(' ')[-1])[:-5] + '_histo.root'
print("Histogram output = ", p.histogram_file)

signal = "signal" in fileName
print("signal = ", signal)

p.sequence = [ldmxcfg.processor_from_file(
    'CnCNtuple.cxx',
    needs=['Ecal_Event', 'Hcal_Event', 'Recon_Event', 'SimCore_Event',
           'Tracking_Event', 'DetDescr'],
    trigger_pass="sim",
    ecal_veto_pass_name='reco',
    ecal_mip_pass_name='reco',
    signal=signal,
)]
p.log_frequency = 1000
