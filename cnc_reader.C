// Full pass over the CnC ntuples for optimize_cnc_punzi.py.
// No RDataFrame or uproot in the container, so the loop is plain C++.
#include <TChain.h>
#include <cstdio>
#include <string>
#include <vector>

namespace cnc {

// summedDet, summedTightIso, ecalBackEnergy, nReadoutHits, showerRMS,
// maxCellDep, stdLayerHit, nStraight, hcalMaxPE
const int NV = 9;
// acc, trig, hit req, then the NV cuts
const int NS = 3 + NV;

// Sequential cutflow counts for nset threshold sets (all cuts are x < thr),
// returned as [set][parity][stage], parity 0 even, 1 odd eventNumber.
// If dump is set, also write rows passing acc and trig that fail at most one
// of the loose cuts: NV floats + parity, float32.
std::vector<double> flow(const std::vector<std::string>& files,
                         const std::vector<double>& thr,
                         const std::vector<int>& minhits,
                         const std::vector<double>& loose,
                         const std::string& dump) {
  int nset = minhits.size();
  std::vector<double> out(nset * 2 * NS, 0.);
  TChain ch("CnCNtuple/cnc");
  for (auto& f : files) ch.Add(f.c_str());

  float fv[NV];
  int nhits, nstraight, ev;
  bool acc, trig;
  ch.SetBranchStatus("*", 0);
  const char* fn[] = {"summedDet", "summedTightIso", "ecalBackEnergy", "",
                      "showerRMS", "maxCellDep", "stdLayerHit", "", "hcalMaxPE"};
  for (int k = 0; k < NV; k++) {
    if (fn[k][0] == 0) continue;
    ch.SetBranchStatus(fn[k], 1);
    ch.SetBranchAddress(fn[k], &fv[k]);
  }
  ch.SetBranchStatus("nReadoutHits", 1); ch.SetBranchAddress("nReadoutHits", &nhits);
  ch.SetBranchStatus("nStraight", 1);    ch.SetBranchAddress("nStraight", &nstraight);
  ch.SetBranchStatus("eventNumber", 1);  ch.SetBranchAddress("eventNumber", &ev);
  ch.SetBranchStatus("acceptance", 1);   ch.SetBranchAddress("acceptance", &acc);
  ch.SetBranchStatus("trigger", 1);      ch.SetBranchAddress("trigger", &trig);

  FILE* fd = dump.empty() ? nullptr : fopen(dump.c_str(), "wb");
  float row[NV + 1];
  Long64_t n = ch.GetEntries();
  for (Long64_t i = 0; i < n; i++) {
    ch.GetEntry(i);
    fv[3] = nhits;
    fv[7] = nstraight;
    int par = ev & 1;
    for (int s = 0; s < nset; s++) {
      double* o = &out[(s * 2 + par) * NS];
      if (!acc) continue;
      o[0]++;
      if (!trig) continue;
      o[1]++;
      if (nhits < minhits[s]) continue;
      o[2]++;
      for (int k = 0; k < NV; k++) {
        if (!(fv[k] < thr[s * NV + k])) break;
        o[3 + k]++;
      }
    }
    if (fd && acc && trig) {
      int nfail = 0;
      for (int k = 0; k < NV; k++) nfail += !(fv[k] < loose[k]);
      if (nfail <= 1) {
        for (int k = 0; k < NV; k++) row[k] = fv[k];
        row[NV] = par;
        fwrite(row, sizeof(float), NV + 1, fd);
      }
    }
  }
  if (fd) fclose(fd);
  return out;
}

}  // namespace cnc
