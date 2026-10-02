import ROOT
ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kFatal
RECO = '/sdf/data/ldmx/private_production/mc26/reco_v492/ecal_pn_v15_8gev/v4.5.4_ecal_pn_run241583_event_sim_pres_reco.root'
PRES = '/sdf/data/ldmx/private_production/mc26/pres_skim/ecal_pn_v15_8gev/v4.5.4_ecal_pn_run241583_event_sim_pres.root'
RUN = 'EventHeader.run_ == 241558'
OK = 'EventHeader.run_ == 241557'   # a neighbouring run in the same file, for contrast
fp = ROOT.TFile.Open(PRES); tp = fp.Get('LDMX_Events')
fr = ROOT.TFile.Open(RECO); tr = fr.Get('LDMX_Events')
for lab, cut in (('bad run 241558', RUN), ('neighbour run 241557', OK)):
    print('== %s' % lab)
    print('  pres_skim events            %6d' % tp.GetEntries(cut))
    print('  pres_skim EcalRecHits empty %6d' % tp.GetEntries(cut + ' && EcalRecHits_sim@.size() == 0'))
    print('  pres_skim EcalDigis   empty %6d' % tp.GetEntries(cut + ' && EcalDigis_sim.channelIDs_@.size() == 0'))
    print('  pres_skim EcalSimHits empty %6d' % tp.GetEntries(cut + ' && EcalSimHits_sim@.size() == 0'))
    print('  reco_v492 events            %6d' % tr.GetEntries(cut))
    print('  reco_v492 n_readout_hits 0  %6d' % tr.GetEntries(cut + ' && EcalVeto_reco.n_readout_hits_ == 0'))
print('run list in file around 241558:', sorted(set(int(x) for x in [0]))) if False else None
n = tp.Draw('EventHeader.run_', '', 'goff')
runs = sorted(set(int(tp.GetV1()[i]) for i in range(n)))
print('runs present in this file: %d, e.g. %s' % (len(runs), runs[:6]))
