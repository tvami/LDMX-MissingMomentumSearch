import ROOT, sys, os, time, re, numpy
#from common_functions import *
from optparse import OptionParser
parser = OptionParser(usage="Usage: python3 %prog [options] sample.txt")
parser.add_option("-c", "--cut", dest="cut", default="Triggerred",
                  help="Bin label to project after (default: Triggerred). E.g. 'ECal veto', Triggerred")
parser.add_option("-e", "--eot", dest="eot", action="store_true", default=False,
                  help="Normalize backgrounds to TARGET_EOT instead of unit area. "
                       "Unit-area normalization makes an EoT factor a no-op, so this "
                       "switches backgrounds to absolute counts. Signal has no EoT "
                       "normalization (yield scales with epsilon^2) and stays unit area.")
(opt,args) = parser.parse_args()

# EoT equivalent of each production, keyed on a filename substring.
TARGET_EOT = 1.5e14
SAMPLE_EOT = {
    "ecal_pn":       1.5e14,
    "target_pn":     1.0e15,
    "target_conv":   1.0e15,
    "ecal_conv":     1.0e15,
}
# fraction of each sample actually reconstructed, so survivors are scaled up
PRES = "/sdf/data/ldmx/private_production/mc26/pres_skim/"
RECO = "/sdf/data/ldmx/private_production/mc26/reco_v492/"
_SUBDIR = {
    "ecal_pn":     "ecal_pn_v15_8gev",
    "target_pn":   "target_pn_v15_8gev",
    "target_conv": "target_conversion_v15_8gev",
    "ecal_conv":   "ecal_conversion_v15_8gev",
}

def eot_weight(fname):
    """Weight to put a background at TARGET_EOT, or None for signal."""
    import glob
    for key, samp_eot in SAMPLE_EOT.items():
        if key in fname:
            w = TARGET_EOT / samp_eot
            sub = _SUBDIR[key]
            ni = len(glob.glob(PRES + sub + "/*.root"))
            no = len(glob.glob(RECO + sub + "/*_reco.root"))
            if ni and no:
                w *= float(ni) / no
            return w
    return None

def addOverflow(h):
    """Add overflow bin content to the last visible bin."""
    n = h.GetNbinsX()
    h.SetBinContent(n, h.GetBinContent(n) + h.GetBinContent(n+1))
    h.SetBinError(n, (h.GetBinError(n)**2 + h.GetBinError(n+1)**2)**0.5)
    h.SetBinContent(n+1, 0)
    h.SetBinError(n+1, 0)

sampleInFile = sys.argv[1]

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kWarning
#ROOT.gStyle.SetPalette(1)
ROOT.gStyle.SetPadRightMargin(.15)
ROOT.gStyle.SetPadTopMargin(0.1)
ROOT.gStyle.SetPadBottomMargin(0.2)
ROOT.gStyle.SetPadLeftMargin(0.15)

# cutFlowLin = True
# cutFlowNorm = False
cutFlowLin = False
cutFlowNorm = True

SamplesArray = []

with open(sampleInFile, "r") as a_file:
  for line in a_file:
    stripped_line = line.strip()
    SamplesArray.append(stripped_line)

fileInArray = []
for sample in SamplesArray:
  fileInArray.append(ROOT.TFile.Open(sample))
  
#dirs = []

f = fileInArray[0]

for i in range(0, fileInArray[0].GetListOfKeys().GetEntries()):
  dirname = f.GetListOfKeys().At(i).GetName()
  curr_dir = f.GetDirectory(dirname)
#  print("dirname: "+dirname)
  if not (curr_dir) :
    continue
  for i in range(0, curr_dir.GetListOfKeys().GetEntries()):
      # Match the plot of interest
      keyname = curr_dir.GetListOfKeys().At(i).GetName()
      # if not ("CutFlow" in keyname):  continue
      keyname2 = keyname
      curr_dir2 = f.GetDirectory(dirname+"/"+keyname)
      if True :
          keyname = curr_dir.GetListOfKeys().At(i).GetName()
#          print(dirname+"/"+keyname)
          curr_dir2 = fileInArray[0].GetDirectory(dirname+"/"+keyname)
          newname = dirname+"/"+keyname
          obj = fileInArray[0].Get(newname)
          obj.SetMarkerStyle(20)
          
          tex2 = ROOT.TLatex(0.15,0.92,"LDMX")
          tex2.SetNDC()
          tex2.SetTextFont(61)
          tex2.SetTextSize(0.06)
          tex2.SetLineWidth(2)


          tex3 = ROOT.TLatex(0.31,0.92,"Simulation"); # for square plots
          tex3.SetNDC()
          tex3.SetTextFont(52)
          tex3.SetTextSize(0.04)
          tex3.SetLineWidth(2)

          tex4 = ROOT.TLatex(0.62,0.92,"1.5#times10^{14} EoT (8 GeV)")
          tex4.SetNDC()
          tex4.SetTextFont(52)
          tex4.SetTextSize(0.025)
          tex4.SetLineWidth(2)
          
          ratioLen = len(sampleInFile)+4
          startTex5 = (120-ratioLen)/120
          tex5 = ROOT.TLatex(startTex5,0.015,"Sample: "+sampleInFile[:-4])
          tex5.SetNDC()
          tex5.SetTextFont(52)
          tex5.SetTextSize(0.017)
          tex5.SetLineWidth(2)

          overFlowText = ROOT.TLatex(0.85,0.15,"overflow")
          overFlowText.SetTextAngle(90)
          overFlowText.SetNDC()
          overFlowText.SetTextFont(52)
          overFlowText.SetTextSize(0.01)
          overFlowText.SetLineWidth(2)
          
          if obj.InheritsFrom("TObject"):
              cutTag = opt.cut.replace(" ", "_")
              outDir = "Compare"+sampleInFile[:-4]
              if not os.path.exists(outDir):
                print("Create dir")
                os.makedirs(outDir)
              if (obj.GetEntries() == 0 ) : continue
              isCutFlow = any(s in keyname for s in ["CutFlow", "Hcal_Back", "Hcal_Reduced"])

              # Special handling for BDT split overlay with ratio (per sample)
              if (obj.ClassName() == "TH2F") and ("BDTSplit" in keyname):
                for iSample, fileIn in enumerate(fileInArray):
                  sampleLabel = SamplesArray[iSample][0:SamplesArray[iSample].find(".root")]
                  myHist = fileIn.Get(newname)
                  if not (myHist) : continue
                  projFail = myHist.ProjectionY(keyname2 + "_BDTFail_"+str(iSample), 1, 1)
                  projPass = myHist.ProjectionY(keyname2 + "_BDTPass_"+str(iSample), 2, 2)
                  projFail.SetDirectory(0)
                  projPass.SetDirectory(0)
                  addOverflow(projFail)
                  addOverflow(projPass)
                  if projFail.Integral() == 0 and projPass.Integral() == 0 : continue

                  failLabel = myHist.GetXaxis().GetBinLabel(1)
                  passLabel = myHist.GetXaxis().GetBinLabel(2)
                  if not failLabel : failLabel = "BDT fail"
                  if not passLabel : passLabel = "BDT pass"

                  nFail = int(projFail.Integral(1, projFail.GetNbinsX()+1))
                  nPass = int(projPass.Integral(1, projPass.GetNbinsX()+1))

                  # Normalize
                  if projFail.Integral() > 0 : projFail.Scale(1./projFail.Integral())
                  if projPass.Integral() > 0 : projPass.Scale(1./projPass.Integral())

                  canvasBDT = ROOT.TCanvas('canvasBDTSplit_'+keyname2+'_'+str(iSample), 'canvasBDTSplit_'+keyname2+'_'+str(iSample), 800, 900)

                  # Upper pad for overlay
                  padTop = ROOT.TPad("padTop_"+str(iSample),"padTop_"+str(iSample), 0, 0.3, 1, 1.0)
                  padTop.SetBottomMargin(0.02)
                  padTop.SetLogy()
                  padTop.Draw()
                  padTop.cd()

                  projFail.SetStats(0)
                  projFail.SetLineColor(ROOT.kRed)
                  projFail.SetMarkerColor(ROOT.kRed)
                  projFail.SetMarkerStyle(20)
                  projFail.SetMarkerSize(0.5)
                  projPass.SetStats(0)
                  projPass.SetLineColor(ROOT.kBlue)
                  projPass.SetMarkerColor(ROOT.kBlue)
                  projPass.SetMarkerStyle(21)
                  projPass.SetMarkerSize(0.5)

                  ymax = numpy.maximum(projFail.GetMaximum(), projPass.GetMaximum()) * 100
                  projFail.GetYaxis().SetRangeUser(0.0000001, ymax*100)
                  projFail.GetYaxis().SetTitle("Normalized events / bin")
                  projFail.GetXaxis().SetLabelSize(0)
                  projFail.GetXaxis().SetTitleSize(0)
                  projFail.Draw("HISTP")
                  projPass.Draw("SAMEHISTP")

                  binWidthBDT = projFail.GetXaxis().GetBinWidth(1)
                  overFlowLocBDT = projFail.GetXaxis().GetBinCenter(projFail.GetNbinsX()) - binWidthBDT/2
                  overFlowLineBDT = ROOT.TLine()
                  overFlowLineBDT.SetLineWidth(2)
                  overFlowLineBDT.SetLineStyle(ROOT.kDashed)
                  overFlowLineBDT.DrawLine(overFlowLocBDT, 0.0000001, overFlowLocBDT, ymax*100)

                  legendBDT = ROOT.TLegend(0.5, 0.70, 0.88, 0.89, "", "brNDC")
                  legendBDT.SetTextFont(42)
                  legendBDT.SetTextSize(0.03)
                  legendBDT.SetBorderSize(0)
                  legendBDT.SetFillStyle(0)
                  legendBDT.SetHeader(sampleLabel)
                  legendBDT.AddEntry(projFail, failLabel + " (N=" + str(nFail) + ")", "LP")
                  legendBDT.AddEntry(projPass, passLabel + " (N=" + str(nPass) + ")", "LP")
                  legendBDT.Draw("SAME")
                  tex2.Draw("SAME")
                  tex3.Draw("SAME")
                  tex4.Draw("SAME")

                  # Lower pad for ratio
                  canvasBDT.cd()
                  padBot = ROOT.TPad("padBot_"+str(iSample),"padBot_"+str(iSample), 0, 0.0, 1, 0.3)
                  padBot.SetTopMargin(0.02)
                  padBot.SetBottomMargin(0.35)
                  padBot.Draw()
                  padBot.cd()

                  ratio = projPass.Clone(keyname2 + "_ratio_"+str(iSample))
                  ratio.SetDirectory(0)
                  ratio.Divide(projFail)
                  ratio.SetLineColor(ROOT.kBlack)
                  ratio.SetMarkerColor(ROOT.kBlack)
                  ratio.SetMarkerStyle(20)
                  ratio.SetMarkerSize(0.5)
                  ratio.SetStats(0)
                  ratio.GetYaxis().SetTitle("Pass / Fail")
                  ratio.GetYaxis().SetTitleSize(0.1)
                  ratio.GetYaxis().SetTitleOffset(0.4)
                  ratio.GetYaxis().SetLabelSize(0.08)
                  ratio.GetYaxis().SetNdivisions(505)
                  ratio.GetXaxis().SetTitleSize(0.12)
                  ratio.GetXaxis().SetLabelSize(0.1)
                  ratio.GetYaxis().SetRangeUser(0, 5)
                  ratio.Draw("P")

                  lineBDT = ROOT.TLine(ratio.GetXaxis().GetXmin(), 1, ratio.GetXaxis().GetXmax(), 1)
                  lineBDT.SetLineStyle(ROOT.kDashed)
                  lineBDT.SetLineWidth(2)
                  lineBDT.Draw("SAME")
                  tex5.Draw("SAME")

                  savePath = outDir+"/"+keyname2+"_"+sampleLabel+"_"+cutTag+".png"
                  os.makedirs(os.path.dirname(savePath), exist_ok=True)
                  canvasBDT.SaveAs(savePath)
                continue

              # Now do the 2D histos
              if (obj.ClassName() == "TH2F"):
                # Auto-detect the bin after the selected cut
                PostCutHistoBin = -1
                for iBinSearch in range(1, obj.GetNbinsX()+1):
                  label = obj.GetXaxis().GetBinLabel(iBinSearch)
                  if opt.cut in label:
                    PostCutHistoBin = iBinSearch + 1
                    break
                if PostCutHistoBin < 0 : PostCutHistoBin = obj.GetNbinsX()

                canvasString = 'canvas'+str(i)
                canvas = ROOT.TCanvas(canvasString, canvasString, 800,800)
                if not ("TrigEff" in keyname or (isCutFlow and cutFlowLin) or "Acceptance" in keyname) : canvas.SetLogy()
                #TADA
                legendStartX = 0.0
                legendEntryForZero = SamplesArray[0][0:SamplesArray[0].find(".root")]
                if ((len(legendEntryForZero)) < 25) :
                  legendStartX = 0.6
                if ((len(legendEntryForZero)) >= 25) :
                  legendStartX = 0.5
                if ((len(legendEntryForZero)) >= 40) :
                  legendStartX = 0.3
                if ((len(legendEntryForZero)) >= 55) :
                  legendStartX = 0.2
                legend =  ROOT.TLegend(legendStartX-0.10,.7,.85,.89,"","brNDC")
                legend.SetTextFont(42)
                legend.SetTextSize(0.03)
                legend.SetBorderSize(1)
                legend.SetBorderSize(0)
                legend.SetLineColor(1)
                legend.SetLineStyle(1)
                legend.SetLineWidth(1)
                legend.SetFillColor(0)
                legend.SetFillStyle(0)
                legend.SetNColumns(2)
                
                histoArray = []
                colors = [ROOT.kRed, ROOT.kGreen, ROOT.kBlue, ROOT.kYellow,
                          ROOT.kMagenta, ROOT.kCyan, ROOT.kGreen+2, ROOT.kBlue-7,
                          ROOT.kGray+1, ROOT.kPink+1]
                # fake index to satisfy ROOT memory allocation
                i = 0
                for fileIn in fileInArray:
#                  print(keyname)
                  if ("N1_" in keyname) :
                    PostCutHisto = fileIn.Get(newname).ProjectionY(keyname2 + "_ProjY"+str(i),PostCutHistoBin,PostCutHistoBin)
                  elif ("Rev_" in keyname) :
                    PostCutHisto = fileIn.Get(newname).ProjectionY(keyname2 + "_ProjY"+str(i),PostCutHistoBin,PostCutHistoBin)
                  elif  ("TrigEff" in keyname):
                    PostCutHisto = fileIn.Get(newname).ProfileY(keyname2 + "_ProfY"+str(i))
                    for indexBin in range(1,PostCutHisto.GetNbinsX()):
                        if ((PostCutHisto.GetBinContent(indexBin) < 0.98) and (PostCutHisto.GetBinError(indexBin) > 0.2 or PostCutHisto.GetBinError(indexBin) == 0)) : PostCutHisto.SetBinContent(indexBin, -1.)
                  elif (isCutFlow or "Acceptance" in keyname):
                    PostCutHisto = fileIn.Get(newname).ProjectionX(keyname2 + "_ProjX"+str(i))
                    PostCutHisto.LabelsOption("v")
                    # PostCutHisto.GetXaxis().SetBinLabel(2,"Non-fiducial")

                  else :
                    PostCutHisto = fileIn.Get(newname).ProjectionY(keyname2 + "_ProjY"+str(i),PostCutHistoBin,PostCutHistoBin)

                  if not ("TrigEff" in keyname or isCutFlow or "Acceptance" in keyname):
                    addOverflow(PostCutHisto)

                  if (PostCutHisto.Integral()> 0 and not "TrigEff" in keyname and not isCutFlow) :
                    _w = eot_weight(SamplesArray[i]) if opt.eot else None
                    if _w is not None:
                      PostCutHisto.Scale(_w)
                    else:
                      PostCutHisto.Scale(1/PostCutHisto.Integral(1,PostCutHisto.GetNbinsX()+1))
                  isSignal = any(s in SamplesArray[i] for s in ["MeV", "0.001", "0.01", "0.1", "p1"])
                  if (PostCutHisto.GetBinContent(1)>0 and isCutFlow and cutFlowNorm) :
                    if isSignal and PostCutHisto.GetBinContent(2)>0:
                      PostCutHisto.Scale(1/PostCutHisto.GetBinContent(2))
                    else:
                      PostCutHisto.Scale(1/PostCutHisto.GetBinContent(1))
                  if (PostCutHisto.GetBinContent(1)>0 and "Acceptance" in keyname) :
                    PostCutHisto.Scale(1/PostCutHisto.GetBinContent(1))
                  if (PostCutHisto.GetBinContent(1)>0 and isCutFlow) :
                    # Print raw counts for background, efficiencies for signal
                    rawCutflow = fileIn.Get(newname).ProjectionX(keyname2 + "_CutFlowRaw"+str(i))
                    rawCutflow.SetDirectory(0)
                    # print(f"Cutflow for sample {SamplesArray[i]}:")
                    # if isSignal:
                    #   normBin = rawCutflow.GetBinContent(2) if rawCutflow.GetBinContent(2)>0 else 1
                    #   print(f"| Cut | Efficiency (norm to bin 2) |")
                    #   print(f"| --- | --- |")
                    #   for binIndex in range(1,rawCutflow.GetNbinsX()+1):
                    #     bin_content = rawCutflow.GetBinContent(binIndex)
                    #     bin_label = rawCutflow.GetXaxis().GetBinLabel(binIndex)
                    #     if bin_content == 0.0: continue
                    #     print(f"| {bin_label} | {bin_content/normBin:.6f} |")
                    # else:
                    #   print(f"| Cut | Events |")
                    #   print(f"| --- | --- |")
                    #   for binIndex in range(1,rawCutflow.GetNbinsX()+1):
                    #     bin_content = rawCutflow.GetBinContent(binIndex)
                    #     bin_label = rawCutflow.GetXaxis().GetBinLabel(binIndex)
                    #     if bin_content == 0.0: continue
                    #     print(f"| {bin_label} | {bin_content:.0f} |")

                  i += 1
                  if (PostCutHisto) : histoArray.append(PostCutHisto)
                for index in range(0, len(histoArray)):
                  histoArray[index].SetStats(0)
                  histoArray[index].SetMarkerStyle(20)
                  histoArray[index].GetXaxis().SetRange(1,histoArray[index].GetNbinsX()+1)
                  if "MaxSector" in keyname:
                    histoArray[index].GetXaxis().SetRange(1,histoArray[index].GetNbinsX())
                  if ("PT" in keyname) :
                    histoArray[index].GetXaxis().SetRangeUser(0.0,1000.0)

                  legendEntry = SamplesArray[index][0:SamplesArray[index].find(".root")]
                  if "1MeV" in legendEntry: legendEntry = "m_{A'} = 1 MeV"
                  if "10MeV" in legendEntry: legendEntry = "m_{A'} = 10 MeV"
                  if "100MeV" in legendEntry: legendEntry = "m_{A'} = 100 MeV"
                  if "1000MeV" in legendEntry: legendEntry = "m_{A'} = 1000 MeV"
                  if "ecal_conv" in legendEntry: legendEntry = "ECal conv."
                  if "CKF" in legendEntry: legendEntry = "Target conv. CKF"
                  if "GSF" in legendEntry: legendEntry = "Target conv. GSF"
                  if "target_conv" in legendEntry: legendEntry = "Target conv."
                  if "target_pn" in legendEntry: legendEntry = "Target PN"
                  if "ecal_pn" in legendEntry: legendEntry = "ECal PN"
                  if "target_en" in legendEntry: legendEntry = "Target EN"
                  legend.AddEntry(histoArray[index],legendEntry,"LP")
                  colorIdx = index % len(colors)
                  histoArray[index].SetLineColor(colors[colorIdx])
                  histoArray[index].SetMarkerColor(colors[colorIdx])
                  histoArray[index].SetTitle("")
                  max_value = 0.0
                  for index2 in range(0, len(histoArray)):
                    if not (histoArray[index2]) : continue
                    max_value = numpy.maximum(max_value,histoArray[index2].GetMaximum())
                  if opt.eot and not isCutFlow and not ("TrigEff" in keyname):
                    # backgrounds are absolute at TARGET_EOT, signal is unit area
                    histoArray[0].GetYaxis().SetTitle("Events / bin")
                    histoArray[0].GetYaxis().SetRangeUser(0.000001, max_value*30)
                  elif cutFlowNorm:
                    histoArray[0].GetYaxis().SetTitle("Normalized events / bin")
                    histoArray[0].GetYaxis().SetRangeUser(0.000001,3000)
                    if "MaxSector" in keyname:
                      histoArray[0].GetYaxis().SetRangeUser(0.001,3000)
                    if "RecoilN" in keyname:
                      histoArray[0].GetYaxis().SetRangeUser(0.000001,500)
                    if "Acceptance" in keyname:
                      histoArray[0].GetYaxis().SetRangeUser(0.000001,1.5)
                  else :
                    histoArray[0].GetYaxis().SetTitle("Events / bin")
                    histoArray[0].GetYaxis().SetRangeUser(0.000001,max_value*1.6)
                  if ("TrigEff" in keyname) :
                    histoArray[0].GetYaxis().SetRangeUser(0.0,1.5)
                    histoArray[0].GetYaxis().SetTitle("Efficiency")
                  if (isCutFlow):
                    if (cutFlowLin or "Acceptance" in keyname) :
                      histoArray[0].GetYaxis().SetRangeUser(0.0,1.30)
                    if (not cutFlowNorm and not cutFlowLin):
                      histoArray[0].GetYaxis().SetRangeUser(0.9,max_value*30)
                  binWidth = histoArray[index].GetXaxis().GetBinWidth(1)
                  firstBinLocXCent = histoArray[index].GetXaxis().GetBinCenter(1)
                  overFlowLocXCent = histoArray[index].GetXaxis().GetBinCenter(histoArray[index].GetNbinsX())
                  overFlowLocX = (overFlowLocXCent - (binWidth)/2)
                  if (isCutFlow or "Acceptance" in keyname) :
                    overFlowLocX = 99999
                  firstBinLoxX = abs(firstBinLocXCent - (binWidth)/2)
                  
                  overFlowLine = ROOT.TLine();
#                  overFlowLine.SetNDC();
                  overFlowLine.SetLineWidth(2);
                  overFlowLine.SetLineStyle(ROOT.kDashed);
                  if "NReadoutHits" in keyname:
                    histoArray[index].Rebin(2)
                  if "Tracking_RecoilP" in keyname:
                    histoArray[index].Rebin(50)
                    histoArray[index].GetXaxis().SetNdivisions(505)
                  histoArray[index].Draw("SAMEPE")
                  if (isCutFlow and not cutFlowLin):
                    histoArray[index].Draw("SAMEHISTOTEXT45")
                  
#                  if (any(substring in keyname2 for substring in ["mass", "pt"])):
#                    histoArray[index].Rebin(2)

                legend.Draw("SAME")
                tex2.Draw("SAME")
                tex3.Draw("SAME")
                tex4.Draw("SAME")
                tex5.Draw("SAME")
                # overFlowText.Draw("SAME")
                overFlowLine.DrawLine(overFlowLocX,histoArray[0].GetMinimum(),overFlowLocX,histoArray[0].GetMaximum())
                isHcalCutFlow = any(s in keyname for s in ["Hcal_Back", "Hcal_Reduced"])
                if isHcalCutFlow:
                    savePath = outDir+"/"+keyname2+"_CutFlow_"+cutTag+".png"
                else:
                    savePath = outDir+"/"+keyname2+"_"+cutTag+".png"
                os.makedirs(os.path.dirname(savePath), exist_ok=True)
                canvas.SaveAs(savePath)
                # canvas.SaveAs(outDir+"/"+keyname2+".pdf")
                # canvas.SaveAs(outDir+"/"+keyname2+".C")

                # Overlay raw cutflow and normalized cutflow from all samples
                if (isCutFlow):
                  ROOT.gStyle.SetPadRightMargin(.09)
                  ROOT.gStyle.SetPadTopMargin(0.1)
                  ROOT.gStyle.SetPadBottomMargin(0.20)
                  ROOT.gStyle.SetPadLeftMargin(0.15)

                  cutflowArray = []
                  cutflowNormArray = []
                  for iSample, fileIn in enumerate(fileInArray):
                    cutflow = fileIn.Get(newname).ProjectionX(keyname2 + "_CutFlow"+str(iSample))
                    cutflow.SetDirectory(0)
                    if cutflow.GetEntries() == 0 : continue
                    cutflow.SetStats(0)
                    cutflow.LabelsOption("v")
                    colorIdx = iSample % len(colors)
                    cutflow.SetLineColor(colors[colorIdx])
                    cutflow.SetMarkerColor(colors[colorIdx])
                    cutflow.SetMarkerStyle(20)
                    cutflowArray.append(cutflow)
                    # Clone for normalized version before any scaling
                    cutflowN = cutflow.Clone(keyname2 + "_CutFlowNorm"+str(iSample))
                    cutflowN.SetDirectory(0)
                    if (cutflowN.GetBinContent(1)>0) : cutflowN.Scale(1/cutflowN.GetBinContent(1))
                    cutflowNormArray.append(cutflowN)

                  # Raw cutflow overlay
                  if len(cutflowArray) > 0:
                    canvasCF = ROOT.TCanvas('canvasCutFlow_'+keyname2, 'canvasCutFlow_'+keyname2, 800, 800)
                    canvasCF.SetLogy()
                    legendCF = ROOT.TLegend(legendStartX,.75,.85,.89,"","brNDC")
                    legendCF.SetTextFont(42)
                    legendCF.SetTextSize(0.017)
                    legendCF.SetBorderSize(0)
                    legendCF.SetFillStyle(0)
                    cfMax = numpy.max([cf.GetMaximum() for cf in cutflowArray])
                    for idx, cf in enumerate(cutflowArray):
                      cf.GetYaxis().SetTitle("Events / bin")
                      cf.GetYaxis().SetRangeUser(1, cfMax*1000)
                      legendEntry = SamplesArray[idx][0:SamplesArray[idx].find(".root")]
                      if "1MeV" in legendEntry: legendEntry = "m_{A'} = 1 MeV"
                      if "10MeV" in legendEntry: legendEntry = "m_{A'} = 10 MeV"
                      if "100MeV" in legendEntry: legendEntry = "m_{A'} = 100 MeV"
                      if "1000MeV" in legendEntry: legendEntry = "m_{A'} = 1000 MeV"
                      if "ecal_conv" in legendEntry: legendEntry = "ECal conv."
                      if "CKF" in legendEntry: legendEntry = "Target conv. CKF"
                      if "GSF" in legendEntry: legendEntry = "Target conv. GSF"
                      if "target_conv" in legendEntry: legendEntry = "Target conv."
                      if "target_pn" in legendEntry: legendEntry = "Target PN"
                      if "ecal_pn" in legendEntry: legendEntry = "ECal PN"
                      if "target_en" in legendEntry: legendEntry = "Target EN"
                      legendCF.AddEntry(cf, legendEntry, "LP")
                      if idx == 0:
                        cf.Draw("HISTOTEXT45")
                      else:
                        cf.Draw("SAMEHISTOTEXT45")
                    legendCF.Draw("SAME")
                    tex2.Draw("SAME")
                    tex3.Draw("SAME")
                    tex4.Draw("SAME")
                    tex5.Draw("SAME")
                    savePath = outDir+"/CutFlow_"+keyname2+"_"+cutTag+".png"
                    os.makedirs(os.path.dirname(savePath), exist_ok=True)
                    canvasCF.SaveAs(savePath)
                    # canvasCF.SaveAs(outDir+"/CutFlow_"+keyname2+".pdf")

                  # Normalized cutflow overlay (efficiency)
                  if len(cutflowNormArray) > 0:
                    canvasCFN = ROOT.TCanvas('canvasCutFlowN_'+keyname2, 'canvasCutFlowN_'+keyname2, 800, 800)
                    legendCFN = ROOT.TLegend(legendStartX,.75,.85,.89,"","brNDC")
                    legendCFN.SetTextFont(42)
                    legendCFN.SetTextSize(0.017)
                    legendCFN.SetBorderSize(0)
                    legendCFN.SetFillStyle(0)
                    for idx, cfn in enumerate(cutflowNormArray):
                      cfn.GetYaxis().SetTitle("Efficiency")
                      legendEntry = SamplesArray[idx][0:SamplesArray[idx].find(".root")]
                      if "1MeV" in legendEntry: legendEntry = "m_{A'} = 1 MeV"
                      if "10MeV" in legendEntry: legendEntry = "m_{A'} = 10 MeV"
                      if "100MeV" in legendEntry: legendEntry = "m_{A'} = 100 MeV"
                      if "1000MeV" in legendEntry: legendEntry = "m_{A'} = 1000 MeV"
                      if "ecal_conv" in legendEntry: legendEntry = "ECal conv."
                      if "CKF" in legendEntry: legendEntry = "Target conv. CKF"
                      if "GSF" in legendEntry: legendEntry = "Target conv. GSF"
                      if "target_conv" in legendEntry: legendEntry = "Target conv."
                      if "target_pn" in legendEntry: legendEntry = "Target PN"
                      if "ecal_pn" in legendEntry: legendEntry = "ECal PN"
                      if "target_en" in legendEntry: legendEntry = "Target EN"
                      legendCFN.AddEntry(cfn, legendEntry, "LP")
                      if idx == 0:
                        cfn.Draw("HISTOTEXT45")
                      else:
                        cfn.Draw("SAMEHISTOTEXT45")
                    legendCFN.Draw("SAME")
                    tex2.Draw("SAME")
                    tex3.Draw("SAME")
                    tex4.Draw("SAME")
                    tex5.Draw("SAME")
                    savePath = outDir+"/CutFlowNorm_"+keyname2+"_"+cutTag+".png"
                    os.makedirs(os.path.dirname(savePath), exist_ok=True)
                    canvasCFN.SaveAs(savePath)
                    # canvasCFN.SaveAs(outDir+"/CutFlowNorm_"+keyname2+".pdf")

                  # Reset pad margins
                  ROOT.gStyle.SetPadRightMargin(.15)
                  ROOT.gStyle.SetPadBottomMargin(0.2)
                  ROOT.gStyle.SetPadLeftMargin(0.15)

                # ProjectionY for Hcal histograms (in addition to cutflow ProjectionX above)
                if isHcalCutFlow:
                  canvasPY = ROOT.TCanvas('canvasProjY_'+keyname2, 'canvasProjY_'+keyname2, 800, 800)
                  canvasPY.SetLogy()
                  legendPY = ROOT.TLegend(legendStartX-0.10,.7,.85,.89,"","brNDC")
                  legendPY.SetTextFont(42)
                  legendPY.SetTextSize(0.03)
                  legendPY.SetBorderSize(0)
                  legendPY.SetFillStyle(0)
                  legendPY.SetNColumns(2)
                  histoPYArray = []
                  for iY, fileIn in enumerate(fileInArray):
                    projY = fileIn.Get(newname).ProjectionY(keyname2 + "_ProjYextra"+str(iY), PostCutHistoBin, PostCutHistoBin)
                    projY.SetDirectory(0)
                    addOverflow(projY)
                    if projY.Integral() > 0:
                      projY.Scale(1/projY.Integral(1, projY.GetNbinsX()+1))
                    histoPYArray.append(projY)
                  if len(histoPYArray) > 0 and any(h.GetEntries() > 0 for h in histoPYArray):
                    max_valuePY = 0.0
                    for idx, h in enumerate(histoPYArray):
                      h.SetStats(0)
                      h.SetMarkerStyle(20)
                      colorIdx = idx % len(colors)
                      h.SetLineColor(colors[colorIdx])
                      h.SetMarkerColor(colors[colorIdx])
                      h.SetTitle("")
                      max_valuePY = numpy.maximum(max_valuePY, h.GetMaximum())
                      legendEntry = SamplesArray[idx][0:SamplesArray[idx].find(".root")]
                      if "1MeV" in legendEntry: legendEntry = "m_{A'} = 1 MeV"
                      if "10MeV" in legendEntry: legendEntry = "m_{A'} = 10 MeV"
                      if "100MeV" in legendEntry: legendEntry = "m_{A'} = 100 MeV"
                      if "1000MeV" in legendEntry: legendEntry = "m_{A'} = 1000 MeV"
                      if "ecal_conv" in legendEntry: legendEntry = "ECal conv."
                      if "CKF" in legendEntry: legendEntry = "Target conv. CKF"
                      if "GSF" in legendEntry: legendEntry = "Target conv. GSF"
                      if "target_conv" in legendEntry: legendEntry = "Target conv."
                      if "target_pn" in legendEntry: legendEntry = "Target PN"
                      if "ecal_pn" in legendEntry: legendEntry = "ECal PN"
                      if "target_en" in legendEntry: legendEntry = "Target EN"
                      legendPY.AddEntry(h, legendEntry, "LP")
                      h.Draw("SAMEPE")
                    histoPYArray[0].GetYaxis().SetTitle("Normalized events / bin")
                    histoPYArray[0].GetYaxis().SetRangeUser(0.000001, max_valuePY*100)
                    legendPY.Draw("SAME")
                    tex2.Draw("SAME")
                    tex3.Draw("SAME")
                    tex4.Draw("SAME")
                    tex5.Draw("SAME")
                    binWidthPY = histoPYArray[0].GetXaxis().GetBinWidth(1)
                    overFlowLocPY = histoPYArray[0].GetXaxis().GetBinCenter(histoPYArray[0].GetNbinsX()) - binWidthPY/2
                    overFlowLinePY = ROOT.TLine()
                    overFlowLinePY.SetLineWidth(2)
                    overFlowLinePY.SetLineStyle(ROOT.kDashed)
                    overFlowLinePY.DrawLine(overFlowLocPY, 0.000001, overFlowLocPY, max_valuePY*100)
                    savePath = outDir+"/"+keyname2+"_"+cutTag+".png"
                    os.makedirs(os.path.dirname(savePath), exist_ok=True)
                    canvasPY.SaveAs(savePath)

print("Done!")