"""Work out which ECal BDT scored the signal reco.

Jihoon's files carry EcalVeto in the pass 'reco_v1' but the run header records
no BDT provenance. Re-run EcalVetoProcessor here with the stock (segmip) BDT
and write both objects out; if the stored disc matches the recomputed one
event by event, the signal was scored with segmip.

  denv fire cfg_probe_signal_bdt.py <signal file>.root
"""
import sys

from LDMX.Framework import ldmxcfg

p = ldmxcfg.Process('probe')

import LDMX.Ecal.ecal_hardcoded_conditions  # noqa: F401,E402
from LDMX.Ecal import EcalGeometry  # noqa: F401,E402
from LDMX.Ecal import vetos  # noqa: E402

p.maxEvents = 200
p.inputFiles = [sys.argv[1]]
p.outputFiles = ['/home/vamitamas/LDMX-CutBasedDM/probe_signal_bdt.root']

# stock segmip BDT: bdt_file / bdt_feature_set left at their defaults
ecalVeto = vetos.EcalVetoProcessor()
ecalVeto.recoil_from_tracking = True
ecalVeto.track_collection = 'RecoilTracksClean'
ecalVeto.track_pass_name = 'reco_v1'
ecalVeto.rec_pass_name = ''
ecalVeto.sim_particles_passname = 'sim'

p.sequence = [ecalVeto]
p.termLogLevel = 2
p.logFrequency = 100
