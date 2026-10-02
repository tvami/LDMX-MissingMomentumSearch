#include "Framework/EventProcessor.h"
#include "Ecal/Event/EcalVetoResult.h"
#include "Ecal/Event/EcalMipResult.h"
#include "Recon/Event/TriggerResult.h"
#include "Hcal/Event/HcalHit.h"
#include "DetDescr/HcalID.h"
#include "Recon/Event/FiducialFlag.h"
#include "Tracking/Event/TrackerVetoResult.h"

#include "TTree.h"

// One row per event with the cut-and-count variables, for offline threshold
// optimization (PLAN_CNC_PUNZI.md). Kept separate from CutBasedDM so the two
// campaigns never share a library.

class CnCNtuple : public framework::Analyzer {
 public:
  CnCNtuple(const std::string& name, framework::Process& p)
      : framework::Analyzer(name, p) {}
  void configure(framework::config::Parameters& ps) final;
  void onProcessStart() final;
  void analyze(const framework::Event& event) final;

 private:
  std::string trigger_pass_;
  std::string ecal_veto_pass_name_;
  std::string ecal_mip_pass_name_;
  bool signal_{false};

  TTree* tree_{nullptr};
  float summedDet_, summedTightIso_, ecalBackEnergy_, showerRMS_, maxCellDep_,
      stdLayerHit_, hcalMaxPE_;
  // ECal BDT score, so the BDT flow can be rebuilt with any non-ECal cuts
  float bdtDisc_;
  int nReadoutHits_, nStraight_, eventNumber_, run_;
  // trackerVeto added for the aligned flow (same non-ECal cuts as the BDT)
  bool acceptance_, trigger_, trackerVeto_;
};

void CnCNtuple::configure(framework::config::Parameters& ps) {
  trigger_pass_ = ps.getParameter<std::string>("trigger_pass", "");
  ecal_veto_pass_name_ = ps.getParameter<std::string>("ecal_veto_pass_name", "");
  ecal_mip_pass_name_ = ps.getParameter<std::string>("ecal_mip_pass_name", "");
  signal_ = ps.getParameter<bool>("signal", false);
}

void CnCNtuple::onProcessStart() {
  getHistoDirectory();
  // owned by the histogram file
  tree_ = new TTree("cnc", "cut-and-count variables");
  tree_->Branch("summedDet", &summedDet_);
  tree_->Branch("summedTightIso", &summedTightIso_);
  tree_->Branch("ecalBackEnergy", &ecalBackEnergy_);
  tree_->Branch("nReadoutHits", &nReadoutHits_);
  tree_->Branch("showerRMS", &showerRMS_);
  tree_->Branch("maxCellDep", &maxCellDep_);
  tree_->Branch("stdLayerHit", &stdLayerHit_);
  tree_->Branch("nStraight", &nStraight_);
  tree_->Branch("hcalMaxPE", &hcalMaxPE_);
  tree_->Branch("acceptance", &acceptance_);
  tree_->Branch("trigger", &trigger_);
  tree_->Branch("trackerVeto", &trackerVeto_);
  tree_->Branch("bdtDisc", &bdtDisc_);
  tree_->Branch("eventNumber", &eventNumber_);
  tree_->Branch("run", &run_);
}

void CnCNtuple::analyze(const framework::Event& event) {
  auto ecalVeto{event.getObject<ldmx::EcalVetoResult>("EcalVeto", ecal_veto_pass_name_)};
  auto trigResult{event.getObject<ldmx::TriggerResult>("Trigger", trigger_pass_)};
  auto hcalRecHits{event.getCollection<ldmx::HcalHit>("HcalRecHits", "")};

  summedDet_ = ecalVeto.getSummedDet();
  summedTightIso_ = ecalVeto.getSummedTightIso();
  ecalBackEnergy_ = ecalVeto.getEcalBackEnergy();
  nReadoutHits_ = ecalVeto.getNReadoutHits();
  showerRMS_ = ecalVeto.getShowerRMS();
  maxCellDep_ = ecalVeto.getMaxCellDep();
  stdLayerHit_ = ecalVeto.getStdLayerHit();

  // -1 if absent; CutBasedDM passes the cut then
  nStraight_ = -1;
  if (event.exists("EcalMipInfo", ecal_mip_pass_name_)) {
    nStraight_ = event.getObject<ldmx::EcalMipResult>("EcalMipInfo", ecal_mip_pass_name_)
                     .getNStraightTracks();
  }

  acceptance_ = true;
  if (signal_) {
    acceptance_ = event.getObject<ldmx::FiducialFlag>("RecoilTruthFiducialFlags", "")
                      .isFiducial();
  }
  trigger_ = trigResult.passed();
  bdtDisc_ = ecalVeto.getDisc();
  // same object and pass as CutBasedDM (veto_pass_name defaults to "")
  trackerVeto_ = event.getObject<ldmx::TrackerVetoResult>("TrackerVeto", "").passesVeto();
  eventNumber_ = event.getEventNumber();
  run_ = event.getEventHeader().getRun();

  // copied from CutBasedDM.cxx, hcalMaxPE only
  float hcalMaxPE{-9999};
  for (const auto hcalHit : hcalRecHits) {
    float maxTime_{50.};
    if (hcalHit.getTime() >= maxTime_) {
      continue;
    }

    float backMinPE_{1.};
    ldmx::HcalID id(hcalHit.getID());
    if ((id.section() == ldmx::HcalID::BACK) &&  (hcalHit.getMinPE() < backMinPE_)) {
      continue;
    }

    float pe = hcalHit.getPE();
    if (hcalMaxPE < pe) {
      hcalMaxPE = pe;
    }
  }
  hcalMaxPE_ = hcalMaxPE;

  tree_->Fill();
}

DECLARE_ANALYZER(CnCNtuple);
