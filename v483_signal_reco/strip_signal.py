"""Strip Jihoon's signal files to the sim record, for re-reco in v4.8.3.

ldmx-sw ignore/drop rules cannot do this: EventFile.cxx reactivates "*" after
cloning, so ROOT still deserialises the v4.5.11 Track branches, which do not
read back under v4.8.3 dictionaries.

libTracking_Event is deliberately NOT loaded - with its dictionary present ROOT
tries to interpret those branches even when disabled. Disabling is by wildcard:
exact names and branch-list removal are both ignored or crash.
"""
import sys
import ROOT

ROOT.gErrorIgnoreLevel = ROOT.kWarning
for lib in ("libFramework", "libDetDescr", "libSimCore_Event",
            "libEcal_Event", "libHcal_Event", "libRecon_Event",
            "libTrigScint_Event"):
    ROOT.gSystem.Load(lib)

# NOTE: EcalSimHits must stay. It is by far the largest collection and the
# ecal digi/rec are not re-run, but RecoilFiducialityProcessor reads it
# (ecal_collection default) to set RecoilTruthFiducialFlags -- without it the
# reco aborts with "TGenCollectionProxy: no proxy object set".
DISABLE = [
    "*_reco_v1*",                 # the stale reco pass
    "TargetSimHits*",
    "MagnetScoringPlaneHits*",
    "TrackerScoringPlaneHits*",
    "HcalScoringPlaneHits*",
]

src, dst = sys.argv[1], sys.argv[2]
fin = ROOT.TFile.Open(src)
tin = fin.Get("LDMX_Events")
if not tin:
    raise SystemExit("no LDMX_Events in %s" % src)

tin.SetBranchStatus("*", 1)
for pat in DISABLE:
    tin.SetBranchStatus(pat, 0)

fout = ROOT.TFile(dst, "RECREATE", "", 9)
tout = tin.CloneTree(-1)
tout.Write("", ROOT.TObject.kOverwrite)
rin = fin.Get("LDMX_Run")
if rin:
    rin.CloneTree(-1).Write("", ROOT.TObject.kOverwrite)

kept = sorted(b.GetName() for b in tout.GetListOfBranches())
print("STRIP %s : %d events, %d branches, stale left %d"
      % (src.split("/")[-1], tout.GetEntries(), len(kept),
         len([k for k in kept if k.endswith("_reco_v1")])))
fout.Close()
fin.Close()
