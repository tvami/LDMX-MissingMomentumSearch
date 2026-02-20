#include "Framework/EventProcessor.h"
#include "Ecal/Event/EcalVetoResult.h"
#include "Ecal/Event/EcalMipResult.h"
#include "Recon/Event/TriggerResult.h"
#include "Hcal/Event/HcalVetoResult.h"
#include "DetDescr/HcalID.h"
#include "SimCore/Event/SimParticle.h"
#include "DetDescr/SimSpecialID.h"
#include "SimCore/Event/SimTrackerHit.h"
#include "Tracking/Event/Track.h"
#include "Tracking/Event/TrackerVetoResult.h"
#include "Recon/Event/FiducialFlag.h"


#include <math.h>

// v0: Just a few cuts, establish minimal scenario
// v1: More strict cuts
// v2: Fix for N-1 plots, fix NReadoutHits binning
// v3: Max cell dep is not depth but deposition, non-fid option
// v4: Adding HCAL PE variables, change to truth level recoil ele momentum info
// v5: Adding Target SP recoil ele variables, trigger eff, Target SP angles
// v6: Add alternative cutflow where fiducial is before trigger, 
//     add BDT score (Gabrielle), BDT vs PE
// v7: Update to latest LDMX-SW, redo trigger consitently
// v8: Moving to v1.4.1
// v9: Add the BDT cutflow too
// v10: Add all events bin to BDT cutflow, change MIP < 3
// v11: Fiducial with getFiducial()
// v12: Have BDT cutflow start with trigger
// v13: Add new cutflow with lin-reg, together with HCAL as start
// v14: Have 34 layers, add tracking plots
// v15: Acceptance plot, and add Acceptance to all cutflows
// v16: Add ignore_fiducial_analysis_, move to recoil from tracking
// v17: Running on resim sample, 17b adding HCAL plots, 
//      print out for surviving everything
// v18: ldmx-sw v4.2.19, adding CnCwithTracking
// v19: ldmx-sw v4.5.11, update for latest changes, add more histograms for
//      BDT and tracking, add reverse direction plots, add more HCAL histograms, 
//      add N-1 plots (commented out for now)
// v20: Add more HCAL histograms with different module requirements, SimParticle recoil info for remaining event
// v20b: Fix the arrays used to get the cutflows for reduced HCAL
// v21: What about 6+1 modules?

class CutBasedDM : public framework::Analyzer {
public:
  CutBasedDM(const std::string& name, framework::Process& p)
  : framework::Analyzer(name, p) {}
  ~CutBasedDM() = default;
  void configure(framework::config::Parameters &ps);
  void setHistLabels(const std::string &name, const std::vector<std::string> &labels);
  void setHistLabelsY(const std::string &name, const std::vector<std::string> &labels);

  void onProcessStart();
  void analyze(const framework::Event& event) final;
  
  std::tuple<int, const ldmx::SimParticle *> getRecoilEle(
    const std::map<int, ldmx::SimParticle> &particleMap);
  std::string trigger_collName_;
  std::string trigger_passName_;
  std::string sp_pass_name_;
  std::string track_pass_name_;
  // std::string tagger_track_collection_;
  std::string recoil_track_collection_;
  bool fiducial_analysis_;
  bool ignore_fiducial_analysis_;
  bool ignore_tagger_analysis_;
  bool signal_;
};


void CutBasedDM::configure(framework::config::Parameters &ps) {
  trigger_collName_ = ps.getParameter<std::string>("trigger_name","Trigger");
  trigger_passName_ = ps.getParameter<std::string>("trigger_pass","");
  sp_pass_name_ = ps.getParameter<std::string>("sp_pass_name","");
  track_pass_name_ = ps.getParameter<std::string>("track_pass_name","");
  recoil_track_collection_ = ps.getParameter<std::string>("recoil_track_collection","");
  fiducial_analysis_ = ps.getParameter<bool>("fiducial_analysis");
  ignore_fiducial_analysis_ = ps.getParameter<bool>("ignore_fiducial_analysis");
  ignore_tagger_analysis_ = ps.getParameter<bool>("ignore_tagger_analysis",false);
  signal_ = ps.getParameter<bool>("signal", true);

  return;
}

void CutBasedDM::setHistLabels(const std::string &name,
  const std::vector<std::string> &labels) {
    auto histo{histograms_.get(name)};
    for (std::size_t ibin{1}; ibin <= labels.size(); ibin++) {
      histo->GetXaxis()->SetBinLabel(ibin, labels[ibin - 1].c_str());
    }
}

void CutBasedDM::setHistLabelsY(const std::string &name,
  const std::vector<std::string> &labels) {
    auto histo{histograms_.get(name)};
    for (std::size_t ibin{1}; ibin <= labels.size(); ibin++) {
      histo->GetYaxis()->SetBinLabel(ibin, labels[ibin - 1].c_str());
    }
}

void CutBasedDM::onProcessStart(){
  getHistoDirectory();
  
  histograms_.create("Acceptance", "", 6, -0.5, 5.5, "", 90, -450.0, 450.0);
  histograms_.create("TrigEffVsMissingE", "Triggered?", 2, -0.5, 1.5, "Missing ECAL energy [MeV]", 100, 0.0, 10000.0);
  histograms_.create("TrigEffVsSPRecoilPTAtTarget", "Triggered?", 2, -0.5, 1.5, "Recoil p_{T} @Target [MeV]", 800, 0.0, 10000.0);
  histograms_.create("RecoilX", "", 20, -0.5, 19.5, "RecoilX @Ecal [mm]", 90, -450.0, 450.0);
  histograms_.create("SPRecoilXAtTarget", "", 20, -0.5, 19.5, "RecoilX @Target [mm]", 90, -450.0, 450.0);
  histograms_.create("AvgLayerHit", "", 20, -0.5, 19.5, "Avg hit layer", 34, -0.5, 33.5);
  histograms_.create("DeepestLayerHit", "", 20, -0.5, 19.5, "Deepest hit layer", 34, -0.5, 33.5);
  histograms_.create("EcalBackEnergy", "", 20, -0.5, 19.5, "Ecal back energy [MeV]", 100, 0.0, 3000.0);
  histograms_.create("EpAng", "", 20, -0.5, 19.5, "EpAng", 100, 0.0, 90.0);
  histograms_.create("EpSep", "", 20, -0.5, 19.5, "EpSep", 100, 0.0, 1000.0);
  histograms_.create("FirstNearPhLayer", "", 20, -0.5, 19.5, "First near PhLayer", 34, -0.5, 33.5);
  histograms_.create("MaxCellDep", "", 20, -0.5, 19.5, "Max cell deposition [MeV]", 100, 0.0, 800.0);
  histograms_.create("NReadoutHits", "", 20, -0.5, 19.5, "#Readout hits", 150, -0.5, 149.5);
  histograms_.create("StdLayerHit", "", 20, -0.5, 19.5, "Std of hit layers", 70, -0.5, 34.5);
  histograms_.create("Straight", "", 20, -0.5, 19.5, "Straight tracks", 15, -0.5, 14.5);
  histograms_.create("LinRegNew", "", 20, -0.5, 19.5, "Linear regression tracks", 15, -0.5, 14.5);
  histograms_.create("SummedDet", "", 20, -0.5, 19.5, "Summed ECAL energy [MeV]", 100, 0.0, 10000.0);
  histograms_.create("SummedTightIso", "", 20, -0.5, 19.5, "Summed ECAL energy with tight iso [MeV]", 100, 0.0, 10000.0);
  histograms_.create("ShowerRMS", "", 20, -0.5, 19.5, "Shower RMS [mm]", 100, 0.0, 250.0);
  histograms_.create("XStd", "", 20, -0.5, 19.5, "Shower RMS_{X} [mm]", 100, 0.0, 250.0);
  histograms_.create("YStd", "", 20, -0.5, 19.5, "Shower RMS_{Y} [mm]", 100, 0.0, 250.0);
  histograms_.create("BDTDiscr", "", 20, -0.5, 19.5, "BDT discriminating score", 100, 0.0, 1.0);
  histograms_.create("BDTDiscrLog", "", 20, -0.5, 19.5, "-log(1-BDT discriminating score)", 100, 0.0, 5.0);
   
  histograms_.create("RecoilTrackPT", "", 20, -0.5, 19.5, "Recoil track p_{T} [MeV]", 50, 0.0, 1000.0);
  histograms_.create("SimRecoilPT", "", 20, -0.5, 19.5, "Sim recoil p_{T} [MeV]", 200, 0.0, 1000.0);
  histograms_.create("SimRecoilPZ", "", 20, -0.5, 19.5, "Sim recoil p_{Z} [MeV]", 800, -10.0, 8010.0);
  histograms_.create("SimRecoilP", "", 20, -0.5, 19.5, "Sim recoil p [MeV]", 2000, 0.0, 10000.0);
  histograms_.create("SPRecoilPTAtTarget", "", 20, -0.5, 19.5, "Recoil p_{T} @Target [MeV]", 50, 0.0, 1000.0);
  histograms_.create("SPRecoilPZAtTarget", "", 20, -0.5, 19.5, "Recoil p_{Z} @Target [MeV]", 800, -10.0, 8010.0);
  histograms_.create("SPRecoilPAtTarget", "", 20, -0.5, 19.5, "Recoil p @Target [MeV]", 800, 0.0, 10000.0);
  histograms_.create("SPRecoilTheta", "", 20, -0.5, 19.5, "Recoil theta @Target", 90, 0.0, 90.0);
  histograms_.create("SPRecoilPhi", "", 20, -0.5, 19.5, "Recoil phi @Target", 360, -180.0, 180.0);


  histograms_.create("RecoilTrackPT_BDTSplit", "", 2, -0.5, 1.5, "Recoil track p_{T} [MeV]", 50, 0.0, 1000.0);
  histograms_.create("RecoilTrackPT_BDTSplit_TrigOnly", "", 2, -0.5, 1.5, "Recoil track p_{T} [MeV]", 50, 0.0, 1000.0);
  histograms_.create("SPRecoilPT_BDTSplit", "", 2, -0.5, 1.5, "Recoil p_{T} @Target [MeV]", 50, 0.0, 1000.0);
  histograms_.create("SPRecoilPT_BDTSplit_TrigOnly", "", 2, -0.5, 1.5, "Recoil p_{T} @Target [MeV]", 50, 0.0, 1000.0);
  histograms_.create("SimRecoilPT_BDTSplit", "", 2, -0.5, 1.5, "Sim recoil p_{T} [MeV]", 200, 0.0, 1000.0);
  histograms_.create("SimRecoilPT_BDTSplit_TrigOnly", "", 2, -0.5, 1.5, "Sim recoil p_{T} [MeV]", 200, 0.0, 1000.0);
  histograms_.create("RecoilTrackPT_BDTLooseSplit", "", 2, -0.5, 1.5, "Recoil track p_{T} [MeV]", 50, 0.0, 1000.0);
  histograms_.create("RecoilTrackPT_BDTLooseSplit_TrigOnly", "", 2, -0.5, 1.5, "Recoil track p_{T} [MeV]", 50, 0.0, 1000.0);
  histograms_.create("SPRecoilPT_BDTLooseSplit", "", 2, -0.5, 1.5, "Recoil p_{T} @Target [MeV]", 50, 0.0, 1000.0);
  histograms_.create("SPRecoilPT_BDTLooseSplit_TrigOnly", "", 2, -0.5, 1.5, "Recoil p_{T} @Target [MeV]", 50, 0.0, 1000.0);
  histograms_.create("SimRecoilPT_BDTLooseSplit", "", 2, -0.5, 1.5, "Sim recoil p_{T} [MeV]", 200, 0.0, 1000.0);
  histograms_.create("SimRecoilPT_BDTLooseSplit_TrigOnly", "", 2, -0.5, 1.5, "Sim recoil p_{T} [MeV]", 200, 0.0, 1000.0);
  histograms_.create("Hcal_Back_MaxPE", "", 20, -0.5, 19.5, "HCAL back max photo-electron hits", 65, -0.5, 64.5);
  histograms_.create("Hcal_Back_MaxPE_Extended", "", 20, -0.5, 19.5, "HCAL back max photo-electron hits", 120, -0.5, 600.5);
  histograms_.create("Hcal_Reduced_MaxPE", "", 20, -0.5, 19.5, "Reduced HCAL max photo-electron hits", 65, -0.5, 64.5);
  histograms_.create("Hcal_Reduced_MaxPE_Extended", "", 20, -0.5, 19.5, "Reduced HCAL max photo-electron hits", 120, -0.5, 600.5);
  histograms_.create("Hcal_Reduced_MaxPE_Upto6Modules", "", 20, -0.5, 19.5, "Reduced HCAL max PE (up to 6 modules)", 65, -0.5, 64.5);
  histograms_.create("Hcal_Reduced_MaxPE_Upto6Modules_Extended", "", 20, -0.5, 19.5, "Reduced HCAL max PE (up to 6 modules)", 120, -0.5, 600.5);
  histograms_.create("Hcal_Reduced_MaxPE_Upto5Modules", "", 20, -0.5, 19.5, "Reduced HCAL max PE (up to 5 modules)", 65, -0.5, 64.5);
  histograms_.create("Hcal_Reduced_MaxPE_Upto5Modules_Extended", "", 20, -0.5, 19.5, "Reduced HCAL max PE (up to 5 modules)", 120, -0.5, 600.5);
  histograms_.create("Hcal_Reduced_MaxPE_Upto4Modules", "", 20, -0.5, 19.5, "Reduced HCAL max PE (up to 4 modules)", 65, -0.5, 64.5);
  histograms_.create("Hcal_Reduced_MaxPE_Upto4Modules_Extended", "", 20, -0.5, 19.5, "Reduced HCAL max PE (up to 4 modules)", 120, -0.5, 600.5);
  histograms_.create("Hcal_Reduced_MaxPE_Upto3Modules", "", 20, -0.5, 19.5, "Reduced HCAL max PE (up to 3 modules)", 65, -0.5, 64.5);
  histograms_.create("Hcal_Reduced_MaxPE_Upto3Modules_Extended", "", 20, -0.5, 19.5, "Reduced HCAL max PE (up to 3 modules)", 120, -0.5, 600.5);
  histograms_.create("Hcal_Reduced_MaxPE_Upto2Modules", "", 20, -0.5, 19.5, "Reduced HCAL max PE (up to 2 modules)", 65, -0.5, 64.5);
  histograms_.create("Hcal_Reduced_MaxPE_Upto2Modules_Extended", "", 20, -0.5, 19.5, "Reduced HCAL max PE (up to 2 modules)", 120, -0.5, 600.5);
  histograms_.create("Hcal_Reduced_MaxPE_Upto1Modules", "", 20, -0.5, 19.5, "Reduced HCAL max PE (up to 1 module)", 65, -0.5, 64.5);
  histograms_.create("Hcal_Reduced_MaxPE_Upto1Modules_Extended", "", 20, -0.5, 19.5, "Reduced HCAL max PE (up to 1 module)", 120, -0.5, 600.5);

  histograms_.create("Hcal_MaxPE", "", 20, -0.5, 19.5, "HCAL max photo-electron hits", 65, -0.5, 64.5);
  histograms_.create("Hcal_MaxPE_Extended", "", 20, -0.5, 19.5, "HCAL max photo-electron hits", 120, -0.5, 600.5);
  histograms_.create("Hcal_TotalPE", "", 20, -0.5, 19.5, "HCAL total photo-electron hits", 100, -0.5, 200.5);
  histograms_.create("Hcal_TotalPE_AboveMax8PE", "", 20, -0.5, 19.5, "HCAL total photo-electron hits (for MaxPE > 8)", 200, -0.5, 400.5);
  histograms_.create("Hcal_MaxTiming", "", 20, -0.5, 19.5, "HCAL timing of the max PE hit", 35, 0.0, 35.0);
  histograms_.create("Hcal_MaxSector", "", 20, -0.5, 19.5, "", 5, -0.5, 4.5);

  histograms_.create("BDTDiscrVsHcalPE_PreS", "HCAL PE", 500, -0.5, 500.5, "BDT discriminating score", 100, 0.0, 1.0);
  histograms_.create("BDTDiscrLogVsHcalPE_PreS", "HCAL PE", 500, -0.5, 500.5, "-log(1-BDT discriminating score)", 100, 0.0, 5.0);
  histograms_.create("BDTDiscrVsHcalPE_PostS", "HCAL PE", 500, -0.5, 500.5, "BDT discriminating score", 100, 0.0, 1.0);
  histograms_.create("BDTDiscrLogVsHcalPE_PostS", "HCAL PE", 500, -0.5, 500.5, "-log(1-BDT discriminating score)", 100, 0.0, 5.0);

  histograms_.create("AltCutFlow_RecoilX", "", 18, -0.5, 17.5, "RecoilX @Ecal [mm]", 90, -450.0, 450.0);
  histograms_.create("StdCutFlow_RecoilX", "", 18, -0.5, 17.5, "RecoilX @Ecal [mm]", 90, -450.0, 450.0);
  histograms_.create("StdCutFlowWithTracking_RecoilX", "", 20, -0.5, 19.5, "RecoilX @Ecal [mm]", 90, -450.0, 450.0);
  histograms_.create("BDTCutFlow_RecoilX", "", 18, -0.5, 17.5, "RecoilX @Ecal [mm]", 90, -450.0, 450.0);
  // histograms_.create("LinRegCutFlow_RecoilX", "",  18, -0.5, 17.5, "RecoilX @Ecal [mm]", 90, -450.0, 450.0);
  // histograms_.create("LinRegCutFlowHcal_RecoilX", "",  18, -0.5, 17.5, "RecoilX @Ecal [mm]", 90, -450.0, 450.0);
 
  histograms_.create("TrackingCutFlow_RecoilX", "", 18, -0.5, 17.5, "RecoilX @Ecal [mm]", 90, -450.0, 450.0);
  histograms_.create("Tracking_TaggerP", "", 18, -0.5, 17.5, "Tagger p [MeV]", 800, 0.0, 10000.0);
  histograms_.create("Tracking_RecoilN", "", 18, -0.5, 17.5, "N_{recoil}", 10, -0.5, 9.5);
  histograms_.create("Tracking_RecoilP", "", 18, -0.5, 17.5, "Recoil p [MeV]", 2000, 0.0, 10000.0);
  histograms_.create("Tracking_RecoilPt", "", 18, -0.5, 17.5, "Recoil p_{T} [MeV]", 200, 0.0, 1000.0);
  histograms_.create("Tracking_RecoilD0", "", 18, -0.5, 17.5, "d_{0} [mm]", 100, -50.0, 50.0);
  histograms_.create("Tracking_RecoilZ0", "", 18, -0.5, 17.5, "z_{0} [mm]", 100, -50.0, 50.0);
  histograms_.create("TrackingCutFlowHcal_RecoilX", "", 18, -0.5, 17.5, "RecoilX @Ecal [mm]", 90, -450.0, 450.0);
  histograms_.create("TrackingHcal_TaggerP", "", 18, -0.5, 17.5, "Tagger p [MeV]", 2000, 0.0, 10000.0);
  histograms_.create("TrackingHcal_RecoilN", "", 18, -0.5, 17.5, "N_{recoil}", 10, -0.5, 9.5);
  histograms_.create("TrackingHcal_RecoilD0", "", 18, -0.5, 17.5, "d_{0} [mm]", 100, -50.0, 50.0);
  histograms_.create("TrackingHcal_RecoilZ0", "", 18, -0.5, 17.5, "z_{0} [mm]", 100, -50.0, 50.0);

  // Reverse direction
  histograms_.create("Rev_RecoilX", "", 20, -0.5, 19.5, "RecoilX [mm]", 90, -450.0, 450.0);
  histograms_.create("Rev_AvgLayerHit", "", 20, -0.5, 19.5, "Avg hit layer", 34, -0.5, 33.5);
  histograms_.create("Rev_DeepestLayerHit", "", 20, -0.5, 19.5, "Deepest hit layer", 34, -0.5, 33.5);
  histograms_.create("Rev_EcalBackEnergy", "", 20, -0.5, 19.5, "Ecal back energy [MeV]", 100, 0.0, 3000.0);
  histograms_.create("Rev_EpAng", "", 20, -0.5, 19.5, "EpAng", 100, 0.0, 90.0);
  histograms_.create("Rev_EpSep", "", 20, -0.5, 19.5, "EpSep", 100, 0.0, 1000.0);
  histograms_.create("Rev_FirstNearPhLayer", "", 20, -0.5, 19.5, "First near PhLayer", 34, -0.5, 33.5);
  histograms_.create("Rev_MaxCellDep", "", 20, -0.5, 19.5, "Max cell deposition [MeV]", 100, 0.0, 800.0);
  histograms_.create("Rev_NReadoutHits", "", 20, -0.5, 19.5, "#Readout hits", 150, -0.5, 149.5);
  histograms_.create("Rev_StdLayerHit", "", 20, -0.5, 19.5, "Std of hit layers", 70, -0.5, 34.5);
  histograms_.create("Rev_Straight", "", 20, -0.5, 19.5, "Straight tracks", 15, -0.5, 14.5);
  // histograms_.create("Rev_LinRegNew", "", 20, -0.5, 19.5, "Linear regression tracks", 15, -0.5, 14.5);
  histograms_.create("Rev_SummedDet", "", 20, -0.5, 19.5, "Summed ECAL energy [MeV]", 100, 0.0, 10000.0);
  histograms_.create("Rev_SummedTightIso", "", 20, -0.5, 19.5, "Summed ECAL energy with tight iso [MeV]", 100, 0.0, 10000.0);
  histograms_.create("Rev_ShowerRMS", "", 20, -0.5, 19.5, "Shower RMS [mm]", 100, 0.0, 250.0);
  histograms_.create("Rev_XStd", "", 20, -0.5, 19.5, "Shower RMS_{X} [mm]", 100, 0.0, 250.0);
  histograms_.create("Rev_YStd", "", 20, -0.5, 19.5, "Shower RMS_{Y} [mm]", 100, 0.0, 250.0);
  histograms_.create("Rev_Hcal_MaxPE", "", 20, -0.5, 19.5, "HCAL max photo-electron hits", 65, -0.5, 64.5);
  histograms_.create("Rev_Hcal_TotalPE", "", 20, -0.5, 19.5, "HCAL total photo-electron hits", 100, -0.5, 200.5);
  histograms_.create("Rev_Hcal_MaxTiming", "", 20, -0.5, 19.5, "HCAL timing of the max PE hit", 35, 0.0, 35.0);
  histograms_.create("Rev_Hcal_MaxSector", "", 20, -0.5, 19.5, "", 5, -0.5, 4.5);

  // N-1 plots
  // histograms_.create("N1_EcalBackEnergy", "", 20, -0.5, 19.5, "Ecal back energy [MeV]", 100, 0.0, 3000.0);
  // histograms_.create("N1_MaxCellDep", "", 20, -0.5, 19.5, "Max cell deposition [MeV]", 100, 0.0, 800.0);
  // histograms_.create("N1_NReadoutHits", "", 20, -0.5, 19.5, "#Readout hits", 150, -0.5, 149.5);
  // histograms_.create("N1_StdLayerHit", "", 20, -0.5, 19.5, "Std of hit layers", 70, -0.5, 34.5);
  // histograms_.create("N1_Straight", "", 20, -0.5, 19.5, "Straight tracks", 15, -0.5, 14.5);
  // histograms_.create("N1_SummedDet", "", 20, -0.5, 19.5, "Summed ECAL energy [MeV]", 100, 0.0, 10000.0);
  // histograms_.create("N1_SummedTightIso", "", 20, -0.5, 19.5, "Summed ECAL energy with tight iso [MeV]", 100, 0.0, 10000.0);
  // histograms_.create("N1_ShowerRMS", "", 20, -0.5, 19.5, "Shower RMS [mm]", 100, 0.0, 250.0);
  // histograms_.create("N1_YStd", "", 20, -0.5, 19.5, "Shower RMS_{Y} [mm]", 100, 0.0, 250.0);
  // histograms_.create("N1_Hcal_MaxPE", "", 20, -0.5, 19.5, "HCAL max photo-electron hits", 65, -0.5, 64.5);
  // histograms_.create("N1_Hcal_TotalPE", "", 20, -0.5, 19.5, "HCAL total photo-electron hits", 100, -0.5, 200.5);
  // histograms_.create("N1_Hcal_MaxTiming", "", 20, -0.5, 19.5, "HCAL timing of the max PE hit", 35, 0.0, 35.0);
  // histograms_.create("N1_Hcal_MaxSector", "", 20, -0.5, 19.5, "", 5, -0.5, 4.5);

  // histograms_.create("N1_EcalBackEnergy", "", 20, -0.5, 19.5, "Ecal back energy [MeV]", 100, 0.0, 3000.0);

  std::vector<std::string> labels = {
    "All / Acceptance",      // 0
    "Fiducial",              // 1
    "Triggerred",            // 2
    "Preselection",          // 3
    "Tracker veto",           // 4
    "ECal veto",              // 5
    "MIP veto ",      // 6
    "HCal veto",    // 7
    };

  if (!fiducial_analysis_) labels.at(1) = "Non-fiducial";

  setHistLabels("AvgLayerHit", labels);
  setHistLabels("DeepestLayerHit", labels);
  setHistLabels("EcalBackEnergy", labels);
  setHistLabels("EpAng", labels);
  setHistLabels("EpSep", labels);
  setHistLabels("FirstNearPhLayer", labels);
  setHistLabels("MaxCellDep", labels);
  setHistLabels("NReadoutHits", labels);
  setHistLabels("StdLayerHit", labels);
  setHistLabels("Straight", labels);
  setHistLabels("LinRegNew", labels);
  setHistLabels("SummedDet", labels);
  setHistLabels("SummedTightIso", labels);
  setHistLabels("ShowerRMS", labels);
  setHistLabels("XStd", labels);
  setHistLabels("YStd", labels);
  setHistLabels("BDTDiscr", labels);
  setHistLabels("BDTDiscrLog", labels);
  setHistLabels("StdCutFlow_RecoilX", labels);

  setHistLabels("RecoilX", labels);
  setHistLabels("RecoilTrackPT", labels);
  setHistLabels("SimRecoilPT", labels);
  setHistLabels("SimRecoilPZ", labels);
  setHistLabels("SimRecoilP", labels);
  setHistLabels("SPRecoilXAtTarget", labels);
  setHistLabels("SPRecoilPTAtTarget", labels);
  setHistLabels("SPRecoilPZAtTarget", labels);
  setHistLabels("SPRecoilPAtTarget", labels);
  setHistLabels("SPRecoilTheta", labels);
  setHistLabels("SPRecoilPhi", labels);
  std::vector<std::string> labels_BDTSplit = {"BDT < 0.99741", "BDT > 0.99741"};
  setHistLabels("RecoilTrackPT_BDTSplit", labels_BDTSplit);
  setHistLabels("RecoilTrackPT_BDTSplit_TrigOnly", labels_BDTSplit);
  setHistLabels("SPRecoilPT_BDTSplit", labels_BDTSplit);
  setHistLabels("SPRecoilPT_BDTSplit_TrigOnly", labels_BDTSplit);
  setHistLabels("SimRecoilPT_BDTSplit", labels_BDTSplit);
  setHistLabels("SimRecoilPT_BDTSplit_TrigOnly", labels_BDTSplit);
  std::vector<std::string> labels_BDTLooseSplit = {"BDT < 0.99", "BDT > 0.99"};
  setHistLabels("RecoilTrackPT_BDTLooseSplit", labels_BDTLooseSplit);
  setHistLabels("RecoilTrackPT_BDTLooseSplit_TrigOnly", labels_BDTLooseSplit);
  setHistLabels("SPRecoilPT_BDTLooseSplit", labels_BDTLooseSplit);
  setHistLabels("SPRecoilPT_BDTLooseSplit_TrigOnly", labels_BDTLooseSplit);
  setHistLabels("SimRecoilPT_BDTLooseSplit", labels_BDTLooseSplit);
  setHistLabels("SimRecoilPT_BDTLooseSplit_TrigOnly", labels_BDTLooseSplit);
  setHistLabels("Hcal_Back_MaxPE", labels);
  setHistLabels("Hcal_Back_MaxPE_Extended", labels);
  setHistLabels("Hcal_Reduced_MaxPE", labels);
  setHistLabels("Hcal_Reduced_MaxPE_Extended", labels);
  setHistLabels("Hcal_Reduced_MaxPE_Upto6Modules", labels);
  setHistLabels("Hcal_Reduced_MaxPE_Upto6Modules_Extended", labels);
  setHistLabels("Hcal_Reduced_MaxPE_Upto5Modules", labels);
  setHistLabels("Hcal_Reduced_MaxPE_Upto5Modules_Extended", labels);
  setHistLabels("Hcal_Reduced_MaxPE_Upto4Modules", labels);
  setHistLabels("Hcal_Reduced_MaxPE_Upto4Modules_Extended", labels);
  setHistLabels("Hcal_Reduced_MaxPE_Upto3Modules", labels);
  setHistLabels("Hcal_Reduced_MaxPE_Upto3Modules_Extended", labels);
  setHistLabels("Hcal_Reduced_MaxPE_Upto2Modules", labels);
  setHistLabels("Hcal_Reduced_MaxPE_Upto2Modules_Extended", labels);
  setHistLabels("Hcal_Reduced_MaxPE_Upto1Modules", labels);
  setHistLabels("Hcal_Reduced_MaxPE_Upto1Modules_Extended", labels);

  setHistLabels("Hcal_MaxPE", labels);
  setHistLabels("Hcal_MaxPE_Extended", labels);
  setHistLabels("Hcal_TotalPE", labels);
  setHistLabels("Hcal_TotalPE_AboveMax8PE", labels);
  setHistLabels("Hcal_MaxTiming", labels);
  setHistLabels("Hcal_MaxSector", labels);

  // setHistLabels("N1_EcalBackEnergy", labels);
  // setHistLabels("N1_MaxCellDep", labels);
  // setHistLabels("N1_NReadoutHits", labels);
  // setHistLabels("N1_StdLayerHit", labels);
  // setHistLabels("N1_Straight", labels);
  // setHistLabels("N1_SummedDet", labels);
  // setHistLabels("N1_SummedTightIso", labels);
  // setHistLabels("N1_ShowerRMS", labels);
  // setHistLabels("N1_YStd", labels);
  // setHistLabels("N1_Hcal_MaxPE", labels);
  // setHistLabels("N1_Hcal_MaxTiming", labels);
  // setHistLabels("N1_Hcal_MaxSector", labels);

  // Reuse same labels for StdCutFlowWithTracking (same cutflow now)
  setHistLabels("StdCutFlowWithTracking_RecoilX", labels);
  
  std::vector<std::string> labels_Rev = {
    "All / Acceptance",      // 0
    "Fiducial",              // 1
    "Triggerred",            // 2
    "HCal veto",    // 3
    "MIP veto",     // 4
    "ECal veto",              // 5
    "Tracker veto",           // 6
    "Preselection",          // 7
    };

  if (!fiducial_analysis_) labels_Rev.at(1) = "Non-fiducial";
  setHistLabels("Rev_AvgLayerHit", labels_Rev);
  setHistLabels("Rev_DeepestLayerHit", labels_Rev);
  setHistLabels("Rev_EcalBackEnergy", labels_Rev);
  setHistLabels("Rev_EpAng", labels_Rev);
  setHistLabels("Rev_EpSep", labels_Rev);
  setHistLabels("Rev_FirstNearPhLayer", labels_Rev);
  setHistLabels("Rev_MaxCellDep", labels_Rev);
  setHistLabels("Rev_NReadoutHits", labels_Rev);
  setHistLabels("Rev_StdLayerHit", labels_Rev);
  setHistLabels("Rev_Straight", labels_Rev);
  // setHistLabels("Rev_LinRegNew", labels_Rev);
  setHistLabels("Rev_SummedDet", labels_Rev);
  setHistLabels("Rev_SummedTightIso", labels_Rev);
  setHistLabels("Rev_ShowerRMS", labels_Rev);
  setHistLabels("Rev_XStd", labels_Rev);
  setHistLabels("Rev_YStd", labels_Rev);
  setHistLabels("Rev_Hcal_MaxPE", labels_Rev);
  setHistLabels("Rev_Hcal_MaxTiming", labels_Rev);
  setHistLabels("Rev_Hcal_MaxSector", labels_Rev);
 

  // enum HcalSection { BACK = 0, TOP = 1, BOTTOM = 2, RIGHT = 3, LEFT = 4 };
  std::vector<std::string> labels_HCALsector = {
    "HCAL BACK",         // 0
    "HCAL TOP",          // 1
    "HCAL BOTTOM",       // 2
    "HCAL RIGHT",        // 3
    "HCAL LEFT",         // 4
    };

  setHistLabelsY("Hcal_MaxSector", labels_HCALsector);
  // setHistLabelsY("N1_Hcal_MaxSector", labels_HCALsector);
  setHistLabelsY("Rev_Hcal_MaxSector", labels_HCALsector);

  std::vector<std::string> labels_accpt = {
      "All",         // 0
      "Min energy",  // 1
      "Min tk hits", // 2
      "Ecal hit",    // 3
      "Hcal hit",    // 4
      "Acceptance"   // 5
      };
  setHistLabels("Acceptance", labels_accpt);

  // All other cutflows reuse the same labels
  setHistLabels("AltCutFlow_RecoilX",labels);
  setHistLabels("BDTCutFlow_RecoilX",labels);
  setHistLabels("TrackingCutFlow_RecoilX",labels);
  setHistLabels("Tracking_TaggerP",labels);
  setHistLabels("Tracking_RecoilN",labels);
  setHistLabels("Tracking_RecoilP",labels);
  setHistLabels("Tracking_RecoilPt",labels);
  setHistLabels("Tracking_RecoilD0",labels);
  setHistLabels("Tracking_RecoilZ0",labels);
  setHistLabels("TrackingCutFlowHcal_RecoilX",labels);
  setHistLabels("TrackingHcal_TaggerP",labels);
  setHistLabels("TrackingHcal_RecoilN",labels);
  setHistLabels("TrackingHcal_RecoilD0",labels);
  setHistLabels("TrackingHcal_RecoilZ0",labels);

} 

void CutBasedDM::analyze(const framework::Event& event) {
  //std::cout << " ---------------------------------------------" << std::endl;
  auto ecalVeto{event.getObject<ldmx::EcalVetoResult>("EcalVeto","")};
  auto mipResult{event.getObject<ldmx::EcalMipResult>("EcalMipInfo","")};
  auto trigResult{event.getObject<ldmx::TriggerResult>(trigger_collName_, trigger_passName_)};
  auto hcalVeto{event.getObject<ldmx::HcalVetoResult>("HcalVeto","")};
  auto trackerVeto{event.getObject<ldmx::TrackerVetoResult>("TrackerVeto","")};
  auto preselection{event.getObject<bool>("EcalPreselectionDecision","ecal_pres")};
  auto hcalRecHits{event.getCollection<ldmx::HcalHit>("HcalRecHits", "")};
  auto targetSpHits{event.getCollection<ldmx::SimTrackerHit>("TargetScoringPlaneHits",sp_pass_name_)};
  auto recoilTrackCollection{event.getCollection<ldmx::Track>(recoil_track_collection_,"")};

  // Compute recoil track pT
  float recoilTrackPt{-9999.};
  if (recoilTrackCollection.size() == 1) {
    auto trk_mom = recoilTrackCollection[0].getMomentum();
    recoilTrackPt = 1000 * std::sqrt(trk_mom[1] * trk_mom[1] + trk_mom[2] * trk_mom[2]);
  }


  bool acceptance{true};
  int fiducial_analysis_flag{-1};
  if (signal_) {
    auto acceptanceChecks{event.getObject<ldmx::FiducialFlag>("RecoilTruthFiducialFlags","")};
    acceptance =  acceptanceChecks.isFiducial();
    fiducial_analysis_flag = acceptanceChecks.getFiducialFlag();
  }

  // Take recoil momentum from SIM particles
  float simPT{-9999.};
  float simPZ{-9999.};
  float simTotMom{-9999.};
  auto particleMap{event.getMap<int, ldmx::SimParticle>("SimParticles","")};
  auto [recoilTrackID, recoilElectron] = CutBasedDM::getRecoilEle(particleMap);
  simPT =   sqrt(recoilElectron->getMomentum()[0] * recoilElectron->getMomentum()[0] +  recoilElectron->getMomentum()[1] * recoilElectron->getMomentum()[1]);
  simPZ = recoilElectron->getMomentum()[2];
  simTotMom = sqrt(simPT*simPT + simPZ*simPZ);

  // auto phiEle =   (180/M_PI)*std::acos(recoilElectron->getMomentum()[1] /simTotMom)-90.;
  // auto thetaEle = (180/M_PI)*std::acos(simPZ/simTotMom);

  //  Same but at the target SP
  float spXAtTarget{-9999};
  float spPTAtTarget{-9999.};
  float spPYAtTarget{-9999.};
  float spPZAtTarget{-9999.};
  float spTotMomAtTarget{-9999.};
  for (ldmx::SimTrackerHit &spHit : targetSpHits) {
    ldmx::SimSpecialID hit_id(spHit.getID());
    if (hit_id.plane() != 1 || spHit.getMomentum()[2] <= 0) continue;

    if (spHit.getTrackID() == recoilTrackID) {
      float p_current = sqrt(spHit.getMomentum()[0]*spHit.getMomentum()[0] + spHit.getMomentum()[1]*spHit.getMomentum()[1] + spHit.getMomentum()[2]*spHit.getMomentum()[2]);
      if (p_current > spTotMomAtTarget) {
        spPYAtTarget  = spHit.getMomentum()[1];
        spPTAtTarget = sqrt(spHit.getMomentum()[0]*spHit.getMomentum()[0] + spHit.getMomentum()[1]*spHit.getMomentum()[1]);
        spPZAtTarget = spHit.getMomentum()[2];
        spTotMomAtTarget = p_current;
        spXAtTarget = spHit.getPosition()[0];
      }
    }
  }
  auto spPhiEleAtTarget =   (180/M_PI)*std::acos(spPYAtTarget/spTotMomAtTarget)-90.;
  auto spThetaEleAtTarget = (180/M_PI)*std::acos(spPZAtTarget/spTotMomAtTarget);
  // //std::cout << " phiEleAtTarget " << phiEleAtTarget << " phiEle " << phiEle
  //  //std::cout << " thetaEleAtTarget " << thetaEleAtTarget << " phiEleAtTarget " << phiEleAtTarget << std::endl;

  // Take recoil momentum from ECAL SP
  // pT2 = ecalVeto.getRecoilMomentum()[0]*ecalVeto.getRecoilMomentum()[0] + ecalVeto.getRecoilMomentum()[1]*ecalVeto.getRecoilMomentum()[1];
  // pZ =  ecalVeto.getRecoilMomentum()[2];


  // HCAL veto calc
  float hcalMaxPE{-9999};
  float hcalBackMaxPE{-9999};
  float hcalReducedMaxPE{-9999};
  float hcalReducedMaxPE_Upto6Modules{-9999};
  float hcalReducedMaxPE_Upto5Modules{-9999};
  float hcalReducedMaxPE_Upto4Modules{-9999};
  float hcalReducedMaxPE_Upto3Modules{-9999};
  float hcalReducedMaxPE_Upto2Modules{-9999};
  float hcalReducedMaxPE_Upto1Modules{-9999};
  float hcalMaxTiming{-9999};
  int hcalMaxSector{-1};
  float hcalTotalPe{0};
  float hcalTotalPeAbove8PE{0};
  
  ldmx::HcalHit defaultMaxHit_;
  defaultMaxHit_.clear();
  defaultMaxHit_.setPE(-9999);
  defaultMaxHit_.setMinPE(-9999);
  defaultMaxHit_.setSection(-9999);
  defaultMaxHit_.setLayer(-9999);
  defaultMaxHit_.setStrip(-9999);
  defaultMaxHit_.setEnd(-999);
  defaultMaxHit_.setTimeDiff(-9999);
  defaultMaxHit_.setToaPos(-9999);
  defaultMaxHit_.setToaNeg(-9999);
  defaultMaxHit_.setAmplitudePos(-9999);
  defaultMaxHit_.setAmplitudeNeg(-9999);

  const ldmx::HcalHit *maxPEHit{&defaultMaxHit_};

  // Loop on the HCAL hits
  //std::cout << " Num of hcalRecHits = " << hcalRecHits.size() << std::endl;
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
    hcalTotalPe += pe;
    if (pe > 8) {
      hcalTotalPeAbove8PE  += pe;
    }

    if (hcalMaxPE < pe) {
      hcalMaxPE = pe;
      maxPEHit = &hcalHit;
    }

    if (id.section() == ldmx::HcalID::BACK && pe > hcalBackMaxPE) {
      hcalBackMaxPE = pe;
      // first 6+1 modules:
      // One module has 8 layers, so I think the layers would be 1->48+8
      if (id.layer() <= 56) {
        hcalReducedMaxPE = pe;
      }
      if (id.layer() <= 48) {
        hcalReducedMaxPE_Upto6Modules = pe;
      }
      if (id.layer() <= 40) {
        hcalReducedMaxPE_Upto5Modules = pe;
      }
      if (id.layer() <= 32) {
        hcalReducedMaxPE_Upto4Modules = pe;
      }
      if (id.layer() <= 24) {
        hcalReducedMaxPE_Upto3Modules = pe;
      }
      if (id.layer() <= 16) {
        hcalReducedMaxPE_Upto2Modules = pe;
      }
      if (id.layer() <= 8) {
        hcalReducedMaxPE_Upto1Modules = pe;
      }
    }
  }

  ldmx::HcalID maxPeId(maxPEHit->getID());
  hcalMaxTiming = maxPEHit->getTime();
  hcalMaxSector =  maxPeId.section();

  // Trigger eff curves
  histograms_.fill("TrigEffVsMissingE", trigResult.passed() , 8000.-ecalVeto.getSummedDet() );
  histograms_.fill("TrigEffVsSPRecoilPTAtTarget", trigResult.passed() , spPTAtTarget );


  // std::cout << "Fiducial = " << ecalVeto.getFiducial() << std::endl;

  // CutFlow here
  bool passedCutsArray[8];
  std::fill(std::begin(passedCutsArray), std::end(passedCutsArray),false);
  passedCutsArray[0]  = acceptance;
  passedCutsArray[1]  = (ignore_fiducial_analysis_ || (fiducial_analysis_ && ecalVeto.getFiducial()) || (!fiducial_analysis_ && !ecalVeto.getFiducial()));
  passedCutsArray[2]  = trigResult.passed();
  passedCutsArray[3]  = preselection;
  passedCutsArray[4]  = trackerVeto.passesVeto();
  passedCutsArray[5]  = (ecalVeto.getDisc() > 0.99741);
  passedCutsArray[6]  = (mipResult.getNStraightTracks() < 3);
  passedCutsArray[7]  = (hcalMaxPE < 8);

  // Fill histograms

  bool has_min_energy       = fiducial_analysis_flag & (1 << 0);
  bool has_min_tracker_hits = fiducial_analysis_flag & (1 << 1);
  bool has_ecal_hit         = fiducial_analysis_flag & (1 << 2);
  bool has_hcal_hit         = fiducial_analysis_flag & (1 << 3);
  if (fiducial_analysis_flag > 0) {
    histograms_.fill("Acceptance", 0. , ecalVeto.getRecoilX() );
    if (has_min_energy) histograms_.fill("Acceptance", 1. , ecalVeto.getRecoilX() );
    if (has_min_tracker_hits) histograms_.fill("Acceptance", 2. , ecalVeto.getRecoilX() );
    if (has_ecal_hit) histograms_.fill("Acceptance", 3. , ecalVeto.getRecoilX() );
    if (has_hcal_hit) histograms_.fill("Acceptance", 4. , ecalVeto.getRecoilX() );
    if (acceptance) histograms_.fill("Acceptance", 5. , ecalVeto.getRecoilX() );
  }
  

  for (size_t i=0;i<sizeof(passedCutsArray);i++) {
    bool allCutsPassedSoFar = true;
    for (size_t j=0;j<=i;j++) {
      if (!passedCutsArray[j]) {
        allCutsPassedSoFar = false;
        break;
      }
    }
    if (allCutsPassedSoFar) {
      // //std::cout 
      //   << " i-th cut = " << i 
      //   << " trigger = " << trigResult.passed() 
      //   << " getRecoilX = " << ecalVeto.getRecoilX() 
      //   << " getSummedDet = " << ecalVeto.getSummedDet()
      //   << " getSummedTightIso = " << ecalVeto.getSummedTightIso() 
      //   << " getEcalBackEnergy = " << ecalVeto.getEcalBackEnergy() 
      //   << " getNReadoutHits = " << ecalVeto.getNReadoutHits()
      //   << " getShowerRMS = " << ecalVeto.getShowerRMS()
      //   << " getYStd = " << ecalVeto.getYStd()
      //   << " getMaxCellDep = " << ecalVeto.getMaxCellDep()
      //   << " getStdLayerHit = " << ecalVeto.getStdLayerHit()
      //   << " getNStraightTracks = " << mipResult.getNStraightTracks()
      //   << " hcalVeto = " << hcalVeto.passesVeto()
      // //std::cout << "hcalMaxPE = " <<  hcalMaxPE << " hcal total" << hcalTotalPe <<  " maxTime = " << hcalMaxTiming << " where = " << hcalMaxSector
      // << std::endl;

      histograms_.fill("RecoilX", i, ecalVeto.getRecoilX() );
      histograms_.fill("AvgLayerHit", i, ecalVeto.getAvgLayerHit() );
      histograms_.fill("DeepestLayerHit", i, ecalVeto.getDeepestLayerHit() );
      histograms_.fill("EcalBackEnergy", i, ecalVeto.getEcalBackEnergy() );
      histograms_.fill("EpAng", i, ecalVeto.getEPAng() );
      histograms_.fill("EpSep", i, ecalVeto.getEPSep() );
      histograms_.fill("FirstNearPhLayer", i, mipResult.getFirstNearPhLayer() );
      histograms_.fill("MaxCellDep", i, ecalVeto.getMaxCellDep() );
      histograms_.fill("NReadoutHits", i, ecalVeto.getNReadoutHits() );
      histograms_.fill("StdLayerHit", i, ecalVeto.getStdLayerHit() );
      histograms_.fill("Straight", i, mipResult.getNStraightTracks() );
      histograms_.fill("LinRegNew", i, mipResult.getNLinRegTracks() );
      histograms_.fill("SummedDet", i, ecalVeto.getSummedDet() );
      histograms_.fill("SummedTightIso", i, ecalVeto.getSummedTightIso() );
      histograms_.fill("ShowerRMS", i, ecalVeto.getShowerRMS() );
      histograms_.fill("XStd", i, ecalVeto.getXStd() );
      histograms_.fill("YStd", i, ecalVeto.getYStd() );
      histograms_.fill("BDTDiscr", i, ecalVeto.getDisc() );
      histograms_.fill("BDTDiscrLog", i, -log(1-ecalVeto.getDisc()) );
      histograms_.fill("StdCutFlow_RecoilX", i, ecalVeto.getRecoilX() );
      histograms_.fill("RecoilTrackPT", i, recoilTrackPt );
      histograms_.fill("SimRecoilPT", i, simPT );
      histograms_.fill("SimRecoilPZ", i, simPZ );
      histograms_.fill("SimRecoilP", i, simTotMom );
      histograms_.fill("SPRecoilXAtTarget", i, spXAtTarget );
      histograms_.fill("SPRecoilPTAtTarget", i, spPTAtTarget );
      histograms_.fill("SPRecoilPZAtTarget", i, spPZAtTarget );
      histograms_.fill("SPRecoilPAtTarget", i, spTotMomAtTarget );
      histograms_.fill("SPRecoilTheta", i, spThetaEleAtTarget );
      histograms_.fill("SPRecoilPhi", i, spPhiEleAtTarget );
      histograms_.fill("Hcal_MaxPE", i, hcalMaxPE );
      histograms_.fill("Hcal_MaxPE_Extended", i, hcalMaxPE );
      // Hcal_Back and Hcal_Reduced histograms moved to their own cutflow loops below
      histograms_.fill("Hcal_TotalPE", i, hcalTotalPe );
      histograms_.fill("Hcal_TotalPE_AboveMax8PE", i, hcalTotalPeAbove8PE );
      histograms_.fill("Hcal_MaxTiming", i, hcalMaxTiming );
      histograms_.fill("Hcal_MaxSector", i, hcalMaxSector );

      if (i==2) {
        histograms_.fill("BDTDiscrVsHcalPE_PreS", hcalMaxPE , ecalVeto.getDisc() );
        histograms_.fill("BDTDiscrLogVsHcalPE_PreS", hcalMaxPE , -log(1-ecalVeto.getDisc()) );
      }
      if (i==5) {
        histograms_.fill("BDTDiscrVsHcalPE_PostS", hcalMaxPE , ecalVeto.getDisc() );
        histograms_.fill("BDTDiscrLogVsHcalPE_PostS", hcalMaxPE , -log(1-ecalVeto.getDisc()) );
      }
    }
  }

  // Cutflow arrays for HCal Back/Reduced histograms,
  // each using their own maxPE for cut #7 instead of hcalMaxPE
  bool passedCutsBack[8];
  std::copy(std::begin(passedCutsArray), std::end(passedCutsArray), std::begin(passedCutsBack));
  passedCutsBack[7] = (hcalBackMaxPE < 8);

  bool passedCutsReduced[8];
  std::copy(std::begin(passedCutsArray), std::end(passedCutsArray), std::begin(passedCutsReduced));
  passedCutsReduced[7] = (hcalReducedMaxPE < 8);

  bool passedCutsReduced6[8];
  std::copy(std::begin(passedCutsArray), std::end(passedCutsArray), std::begin(passedCutsReduced6));
  passedCutsReduced6[7] = (hcalReducedMaxPE_Upto6Modules < 8);

  bool passedCutsReduced5[8];
  std::copy(std::begin(passedCutsArray), std::end(passedCutsArray), std::begin(passedCutsReduced5));
  passedCutsReduced5[7] = (hcalReducedMaxPE_Upto5Modules < 8);

  bool passedCutsReduced4[8];
  std::copy(std::begin(passedCutsArray), std::end(passedCutsArray), std::begin(passedCutsReduced4));
  passedCutsReduced4[7] = (hcalReducedMaxPE_Upto4Modules < 8);

  bool passedCutsReduced3[8];
  std::copy(std::begin(passedCutsArray), std::end(passedCutsArray), std::begin(passedCutsReduced3));
  passedCutsReduced3[7] = (hcalReducedMaxPE_Upto3Modules < 8);

  bool passedCutsReduced2[8];
  std::copy(std::begin(passedCutsArray), std::end(passedCutsArray), std::begin(passedCutsReduced2));
  passedCutsReduced2[7] = (hcalReducedMaxPE_Upto2Modules < 8);

  bool passedCutsReduced1[8];
  std::copy(std::begin(passedCutsArray), std::end(passedCutsArray), std::begin(passedCutsReduced1));
  passedCutsReduced1[7] = (hcalReducedMaxPE_Upto1Modules < 8);

  for (size_t i = 0; i < 8; i++) {
    auto allPassed = [&](bool* arr, size_t idx) {
      for (size_t j = 0; j <= idx; j++) { if (!arr[j]) return false; }
      return true;
    };
    if (allPassed(passedCutsBack, i)) {
      histograms_.fill("Hcal_Back_MaxPE", i, hcalBackMaxPE);
      histograms_.fill("Hcal_Back_MaxPE_Extended", i, hcalBackMaxPE);
    }
    if (allPassed(passedCutsReduced, i)) {
      histograms_.fill("Hcal_Reduced_MaxPE", i, hcalReducedMaxPE);
      histograms_.fill("Hcal_Reduced_MaxPE_Extended", i, hcalReducedMaxPE);
    }
    if (allPassed(passedCutsReduced6, i)) {
      histograms_.fill("Hcal_Reduced_MaxPE_Upto6Modules", i, hcalReducedMaxPE_Upto6Modules);
      histograms_.fill("Hcal_Reduced_MaxPE_Upto6Modules_Extended", i, hcalReducedMaxPE_Upto6Modules);
    }
    if (allPassed(passedCutsReduced5, i)) {
      histograms_.fill("Hcal_Reduced_MaxPE_Upto5Modules", i, hcalReducedMaxPE_Upto5Modules);
      histograms_.fill("Hcal_Reduced_MaxPE_Upto5Modules_Extended", i, hcalReducedMaxPE_Upto5Modules);
    }
    if (allPassed(passedCutsReduced4, i)) {
      histograms_.fill("Hcal_Reduced_MaxPE_Upto4Modules", i, hcalReducedMaxPE_Upto4Modules);
      histograms_.fill("Hcal_Reduced_MaxPE_Upto4Modules_Extended", i, hcalReducedMaxPE_Upto4Modules);
    }
    if (allPassed(passedCutsReduced3, i)) {
      histograms_.fill("Hcal_Reduced_MaxPE_Upto3Modules", i, hcalReducedMaxPE_Upto3Modules);
      histograms_.fill("Hcal_Reduced_MaxPE_Upto3Modules_Extended", i, hcalReducedMaxPE_Upto3Modules);
    }
    if (allPassed(passedCutsReduced2, i)) {
      histograms_.fill("Hcal_Reduced_MaxPE_Upto2Modules", i, hcalReducedMaxPE_Upto2Modules);
      histograms_.fill("Hcal_Reduced_MaxPE_Upto2Modules_Extended", i, hcalReducedMaxPE_Upto2Modules);
    }
    if (allPassed(passedCutsReduced1, i)) {
      histograms_.fill("Hcal_Reduced_MaxPE_Upto1Modules", i, hcalReducedMaxPE_Upto1Modules);
      histograms_.fill("Hcal_Reduced_MaxPE_Upto1Modules_Extended", i, hcalReducedMaxPE_Upto1Modules);
    }
  }

  // BDT split plots (0.99741), after cuts 0-4 (up to TrackerVeto)
  if (passedCutsArray[0] && passedCutsArray[1] && passedCutsArray[2] &&
      passedCutsArray[3] && passedCutsArray[4]) {
    int bdtBin = (ecalVeto.getDisc() > 0.99741) ? 1 : 0;
    histograms_.fill("RecoilTrackPT_BDTSplit", bdtBin, recoilTrackPt);
    histograms_.fill("SPRecoilPT_BDTSplit", bdtBin, spPTAtTarget);
    histograms_.fill("SimRecoilPT_BDTSplit", bdtBin, simPT);
    int bdtBin99 = (ecalVeto.getDisc() > 0.99) ? 1 : 0;
    histograms_.fill("RecoilTrackPT_BDTLooseSplit", bdtBin99, recoilTrackPt);
    histograms_.fill("SPRecoilPT_BDTLooseSplit", bdtBin99, spPTAtTarget);
    histograms_.fill("SimRecoilPT_BDTLooseSplit", bdtBin99, simPT);
  }

  // BDT split plots, after trigger only (cuts 0-2)
  if (passedCutsArray[0] && passedCutsArray[1] && passedCutsArray[2]) {
    int bdtBin = (ecalVeto.getDisc() > 0.99741) ? 1 : 0;
    histograms_.fill("RecoilTrackPT_BDTSplit_TrigOnly", bdtBin, recoilTrackPt);
    histograms_.fill("SPRecoilPT_BDTSplit_TrigOnly", bdtBin, spPTAtTarget);
    histograms_.fill("SimRecoilPT_BDTSplit_TrigOnly", bdtBin, simPT);
    int bdtBin99 = (ecalVeto.getDisc() > 0.99) ? 1 : 0;
    histograms_.fill("RecoilTrackPT_BDTLooseSplit_TrigOnly", bdtBin99, recoilTrackPt);
    histograms_.fill("SPRecoilPT_BDTLooseSplit_TrigOnly", bdtBin99, spPTAtTarget);
    histograms_.fill("SimRecoilPT_BDTLooseSplit_TrigOnly", bdtBin99, simPT);
  }

  // All other cutflows now use the same 8-bin structure
  for (size_t i=0;i<sizeof(passedCutsArray);i++) {
    bool allCutsPassedSoFar = true;
    for (size_t j=0;j<=i;j++) {
      if (!passedCutsArray[j]) {
        allCutsPassedSoFar = false;
        break;
      }
    }
    if (allCutsPassedSoFar) {
      histograms_.fill("AltCutFlow_RecoilX", i, ecalVeto.getRecoilX() );
      histograms_.fill("BDTCutFlow_RecoilX", i, ecalVeto.getRecoilX() );
      histograms_.fill("StdCutFlowWithTracking_RecoilX", i, ecalVeto.getRecoilX() );
      histograms_.fill("TrackingCutFlow_RecoilX", i, ecalVeto.getRecoilX() );
      histograms_.fill("TrackingCutFlowHcal_RecoilX", i, ecalVeto.getRecoilX() );
      // if (i == (sizeof(passedCutsArray)-1) && !signal_) {
      if (i == (sizeof(passedCutsArray)-1) && false) {
        std::cout << " This bkg event survived all the cuts!!!" << std::endl;
        std::cout << "  Event info: hcalMaxPE=" << hcalMaxPE
                  << " BDTdisc=" << ecalVeto.getDisc()
                  << " nStraightTracks=" << mipResult.getNStraightTracks()
                  << " recoilSimPT=" << simPT << " recoilSimPZ=" << simPZ
                  << " recoilTrackPT=" << recoilTrackPt
                  << std::endl;
        std::cout << "  --- SimParticles dump ---" << std::endl;
        for (const auto &[trackID, particle] : particleMap) {
          auto mom = particle.getMomentum();
          auto vtx = particle.getVertex();
          auto endVtx = particle.getEndPoint();
          float pT = sqrt(mom[0]*mom[0] + mom[1]*mom[1]);
          float p  = sqrt(pT*pT + mom[2]*mom[2]);
          float energy = particle.getEnergy();
          std::cout << "  trackID=" << trackID
                    << " pdgID=" << particle.getPdgID()
                    << " processType=" << static_cast<int>(particle.getProcessType())
                    << " E=" << energy << " p=" << p << " pT=" << pT << " pZ=" << mom[2]
                    << " vtx=(" << vtx[0] << "," << vtx[1] << "," << vtx[2] << ")"
                    << " endVtx=(" << endVtx[0] << "," << endVtx[1] << "," << endVtx[2] << ")"
                    << " nDaughters=" << particle.getDaughters().size()
                    << " nParents=" << particle.getParents().size()
                    << std::endl;
        }
        std::cout << "  --- End SimParticles dump ---" << std::endl;
      }
    }
  }

  // --------------------------------------------------------------------------
  // Reverse cutflow, i.e. start with the last cut from the original cutflow
  bool passedCutsArrayReverse[8];
  std::fill(std::begin(passedCutsArrayReverse), std::end(passedCutsArrayReverse),false);
  passedCutsArrayReverse[0]  = acceptance;
  passedCutsArrayReverse[1]  = (ignore_fiducial_analysis_ || (fiducial_analysis_ && ecalVeto.getFiducial()) || (!fiducial_analysis_ && !ecalVeto.getFiducial()));
  passedCutsArrayReverse[2]  = trigResult.passed();
  passedCutsArrayReverse[3]  = (hcalMaxPE < 8);
  passedCutsArrayReverse[4]  = (mipResult.getNStraightTracks() < 3);
  passedCutsArrayReverse[5]  = (ecalVeto.getDisc() > 0.99741);
  passedCutsArrayReverse[6]  = trackerVeto.passesVeto();
  passedCutsArrayReverse[7]  = preselection;

  for (size_t i=0;i<sizeof(passedCutsArrayReverse);i++) {
    bool allCutsPassedSoFar = true;
    for (size_t j=0;j<=i;j++) {
      if (!passedCutsArrayReverse[j]) {
        allCutsPassedSoFar = false;
        break;
      }
    }
    if (allCutsPassedSoFar) {
      histograms_.fill("Rev_AvgLayerHit", i, ecalVeto.getAvgLayerHit() );
      histograms_.fill("Rev_DeepestLayerHit", i, ecalVeto.getDeepestLayerHit() );
      histograms_.fill("Rev_EcalBackEnergy", i, ecalVeto.getEcalBackEnergy() );
      histograms_.fill("Rev_EpAng", i, ecalVeto.getEPAng() );
      histograms_.fill("Rev_EpSep", i, ecalVeto.getEPSep() );
      histograms_.fill("Rev_FirstNearPhLayer", i, mipResult.getFirstNearPhLayer() );
      histograms_.fill("Rev_MaxCellDep", i, ecalVeto.getMaxCellDep() );
      histograms_.fill("Rev_NReadoutHits", i, ecalVeto.getNReadoutHits() );
      histograms_.fill("Rev_StdLayerHit", i, ecalVeto.getStdLayerHit() );
      histograms_.fill("Rev_Straight", i, mipResult.getNStraightTracks() );
      histograms_.fill("Rev_SummedDet", i, ecalVeto.getSummedDet() );
      histograms_.fill("Rev_SummedTightIso", i, ecalVeto.getSummedTightIso() );
      histograms_.fill("Rev_ShowerRMS", i, ecalVeto.getShowerRMS() );
      histograms_.fill("Rev_XStd", i, ecalVeto.getXStd() );
      histograms_.fill("Rev_YStd", i, ecalVeto.getYStd() );
      histograms_.fill("Rev_Hcal_MaxPE", i, hcalMaxPE );
      histograms_.fill("Rev_Hcal_TotalPE", i, hcalTotalPe );
      histograms_.fill("Rev_Hcal_MaxTiming", i, hcalMaxTiming );
      histograms_.fill("Rev_Hcal_MaxSector", i, hcalMaxSector );
    }
  }
}

std::tuple<int, const ldmx::SimParticle *> CutBasedDM::getRecoilEle(
    const std::map<int, ldmx::SimParticle> &particleMap) {
  // The recoil electron is "produced" in the dark brem geneartion
  for (const auto &[trackID, particle] : particleMap) {
    if (particle.getPdgID() == 11 and particle.getProcessType() == ldmx::SimParticle::ProcessType::eDarkBrem) {
      return {trackID, &particle};
    }   
  }

  // // only get here if recoil electron was not "produced" by dark brem
  // //   in this case (bkgd), we interpret the primary electron as also the recoil
  // //   electron
  // ldmx::SimParticle::ProcessType::Primary
  return {1, &(particleMap.at(1))};
}

DECLARE_ANALYZER(CutBasedDM);
