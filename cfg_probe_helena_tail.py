"""Re-score background with helena and write out the veto, to inspect the tail.

Purpose: find out whether helena's score saturates at 1.0f. EcalVetoResult
stores disc as a float, so anything within ~6e-8 of 1 rounds to exactly 1 and
-log(1-disc) diverges. If a sizeable number of background events sit at 1.0f
then "the cut leaving 1 event" is not resolvable and a rescaled score is needed.

  denv fire cfg_probe_helena_tail.py <background reco file>.root
"""
import sys

from LDMX.Framework import ldmxcfg

p = ldmxcfg.Process('probe')

import LDMX.Ecal.ecal_hardcoded_conditions  # noqa: F401,E402
from LDMX.Ecal import EcalGeometry  # noqa: F401,E402
from LDMX.Ecal import vetos  # noqa: E402

p.maxEvents = -1
p.skipCorruptedInputFiles = True
p.inputFiles = [sys.argv[1]]
p.outputFiles = ['/home/vamitamas/Samples8GeV/probe_helena_tail.root']

ecalVeto = vetos.EcalVetoProcessor()
ecalVeto.bdt_file = '/home/vamitamas/LDMX-CutBasedDM/helena.onnx'
ecalVeto.bdt_feature_set = 'helena'
ecalVeto.recoil_from_tracking = True
ecalVeto.track_collection = 'RecoilTracksClean'
ecalVeto.track_pass_name = 'reco'
ecalVeto.rec_pass_name = ''
ecalVeto.sim_particles_passname = 'sim'

# only the veto object is needed downstream
p.keep = ["drop .*"]
p.outputFiles = ['/home/vamitamas/Samples8GeV/probe_helena_tail.root']
p.keep = ["drop .*SimHits.*", "drop .*ScoringPlaneHits.*", "drop EcalDigis.*",
          "drop EcalRecHits.*", "drop HcalRecHits.*", "drop HcalDigis.*"]

p.sequence = [ecalVeto]
p.termLogLevel = 2
p.logFrequency = 20000
