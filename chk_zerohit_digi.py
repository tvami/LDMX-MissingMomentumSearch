import ROOT
ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kFatal
PRES = '/sdf/data/ldmx/private_production/mc26/pres_skim/ecal_pn_v15_8gev/v4.5.4_ecal_pn_run241583_event_sim_pres.root'
f = ROOT.TFile.Open(PRES); t = f.Get('LDMX_Events')
groups = (('bad run, rec EMPTY  ', 'EventHeader.run_ == 241558 && EcalRecHits_sim@.size() == 0'),
          ('bad run, rec present', 'EventHeader.run_ == 241558 && EcalRecHits_sim@.size() > 0'),
          ('clean run 241557    ', 'EventHeader.run_ == 241557'))
def dist(expr, cut):
    n = t.Draw(expr, cut, 'goff')
    v = [t.GetV1()[i] for i in range(n)]
    c = {}
    for x in v: c[x] = c.get(x, 0) + 1
    return sorted(c.items(), key=lambda kv: -kv[1])[:4]
for lab, cut in groups:
    print('== %s  events %d' % (lab, t.GetEntries(cut)))
    print('   sample_of_interest   ', dist('EcalDigis_sim.sample_of_interest_', cut))
    print('   num_samples_per_digi ', dist('EcalDigis_sim.num_samples_per_digi_', cut))
    print('   version              ', dist('EcalDigis_sim.version_', cut))
    n = t.Draw('EcalDigis_sim.channel_ids_@.size()', cut, 'goff')
    v = sorted(t.GetV1()[i] for i in range(n))
    print('   digi channels median %.0f' % v[len(v)//2])
    n = t.Draw('Sum$(EcalSimHits_sim.edep_)', cut, 'goff')
    v = sorted(t.GetV1()[i] for i in range(n))
    print('   sim Edep median %.1f MeV' % v[len(v)//2])
