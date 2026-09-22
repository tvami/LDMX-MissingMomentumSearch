import ROOT, sys, os, time, re, numpy
#from common_functions import *
from optparse import OptionParser
parser = OptionParser(usage="Usage: python3 %prog sample.txt")
(opt,args) = parser.parse_args()

sampleInFile = sys.argv[1]

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kWarning
#ROOT.gStyle.SetPalette(1)

SamplesArray = []

fileIn = ROOT.TFile.Open(sampleInFile)

for i in range(0, fileIn.GetListOfKeys().GetEntries()):
  dirname = fileIn.GetListOfKeys().At(i).GetName()
  curr_dir = fileIn.GetDirectory(dirname)
  if not (curr_dir) :
    continue
  for i in range(0, curr_dir.GetListOfKeys().GetEntries()):
      keyname = curr_dir.GetListOfKeys().At(i).GetName()
      newname = dirname+"/"+keyname
      # if not ("Trig" in keyname) : continue
      if True :
          keyname2 = keyname
#          print(newname)
          ROOT.gStyle.SetPadRightMargin(.15)
          ROOT.gStyle.SetPadTopMargin(0.1)
          ROOT.gStyle.SetPadBottomMargin(0.14)
          ROOT.gStyle.SetPadLeftMargin(0.15)
          obj = fileIn.Get(newname)
          obj.SetMarkerStyle(20)
          
          tex2 = ROOT.TLatex(0.15,0.92,"LDMX")
          tex2.SetNDC()
          tex2.SetTextFont(61)
          tex2.SetTextSize(0.0675)
          tex2.SetLineWidth(2)

          
          tex3 = ROOT.TLatex(0.33,0.92,"Simulation") # for square plots
          tex3.SetNDC()
          tex3.SetTextFont(52)
          tex3.SetTextSize(0.0485)
          tex3.SetLineWidth(2)
          
          tex4 = ROOT.TLatex(0.57,0.92,"1.5#times10^{14} EOT (8 GeV)")
          tex4.SetNDC()
          tex4.SetTextFont(52)
          tex4.SetTextSize(0.03)
          tex4.SetLineWidth(2)
          
          ratioLen = len(sampleInFile)+4
          startTex5 = (120-ratioLen)/120
          # print(startTex5)
          tex5 = ROOT.TLatex(startTex5,0.015,"Sample: "+sampleInFile[:-5])
          tex5.SetNDC()
          tex5.SetTextFont(52)
          tex5.SetTextSize(0.017)
          tex5.SetLineWidth(2)

          overFlowText = ROOT.TLatex(0.836,0.15,"OF")
#          overFlowText.SetTextAngle(-30)
          overFlowText.SetNDC()
          overFlowText.SetTextFont(52)
          overFlowText.SetTextSize(0.01)
          overFlowText.SetLineWidth(2)
          
          if obj.InheritsFrom("TObject"):
              if not os.path.exists(os.path.dirname("Compare"+sampleInFile[:-5]+"/a.png")):
                print("Create dir")
                os.makedirs(os.path.dirname("Compare"+sampleInFile[:-5]+"/"))
              if (obj.GetEntries() == 0 ) : continue

              # Special handling for BDT split overlay with ratio
              if (obj.ClassName() == "TH2F") and ("BDTSplit" in keyname):
                myHist = fileIn.Get(newname)
                if not (myHist) : continue
                projFail = myHist.ProjectionY(keyname2 + "_BDTFail", 1, 1)
                projPass = myHist.ProjectionY(keyname2 + "_BDTPass", 2, 2)
                projFail.SetDirectory(0)
                projPass.SetDirectory(0)
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

                canvasBDT = ROOT.TCanvas('canvasBDTSplit_'+keyname2, 'canvasBDTSplit_'+keyname2, 800, 900)

                # Upper pad for overlay
                padTop = ROOT.TPad("padTop","padTop", 0, 0.3, 1, 1.0)
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
                projFail.GetYaxis().SetRangeUser(0.0000001, ymax)
                projFail.GetYaxis().SetTitle("Normalized events / bin")
                projFail.GetXaxis().SetLabelSize(0)
                projFail.GetXaxis().SetTitleSize(0)
                projFail.Draw("HISTP")
                projPass.Draw("SAMEHISTP")

                legendBDT = ROOT.TLegend(0.5, 0.75, 0.88, 0.89, "", "brNDC")
                legendBDT.SetTextFont(42)
                legendBDT.SetTextSize(0.03)
                legendBDT.SetBorderSize(0)
                legendBDT.SetFillStyle(0)
                legendBDT.AddEntry(projFail, failLabel + " (N=" + str(nFail) + ")", "LP")
                legendBDT.AddEntry(projPass, passLabel + " (N=" + str(nPass) + ")", "LP")
                legendBDT.Draw("SAME")
                tex2.Draw("SAME")
                tex3.Draw("SAME")
                tex4.Draw("SAME")

                # Lower pad for ratio
                canvasBDT.cd()
                padBot = ROOT.TPad("padBot","padBot", 0, 0.0, 1, 0.3)
                padBot.SetTopMargin(0.02)
                padBot.SetBottomMargin(0.35)
                padBot.Draw()
                padBot.cd()

                ratio = projPass.Clone(keyname2 + "_ratio")
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

                canvasBDT.SaveAs("Compare"+sampleInFile[:-5]+"/"+keyname2+".png")
                continue

              # Now do the 2D histos
              if (obj.ClassName() == "TH2F"):
              
                canvasString = 'canvas'+str(i)
                canvas = ROOT.TCanvas(canvasString, canvasString, 800,800)
                canvas.SetLogy()
                legendStartX = 0.5
                legend =  ROOT.TLegend(legendStartX,.75,.85,.89,"","brNDC")
                legend.SetTextFont(42)
                legend.SetTextSize(0.017)
                legend.SetBorderSize(1)
                legend.SetBorderSize(0)
                legend.SetLineColor(1)
                legend.SetLineStyle(1)
                legend.SetLineWidth(1)
                legend.SetFillColor(0)
#                legend.SetFillStyle(1001)
                legend.SetFillStyle(0)
                
                myHist = fileIn.Get(newname)
                if not (myHist) : continue
                cutflow = myHist.ProjectionX()
                projections = []  # keep projections alive for drawing
                max = 0.0
                nCuts = myHist.GetNbinsX()
                colors = [ROOT.kBlack, ROOT.kRed, ROOT.kBlue, ROOT.kGreen+2,
                          ROOT.kMagenta, ROOT.kCyan+1, ROOT.kOrange+1, ROOT.kViolet,
                          ROOT.kTeal+2, ROOT.kPink+1]
                for iBin in range(1, nCuts+1) :
                  projY = myHist.ProjectionY(keyname2 + "_ProjY"+str(iBin), iBin, iBin)
                  projY.SetDirectory(0)  # detach from file so ROOT doesn't delete it
                  projY.SetMarkerStyle(20)
                  if projY.Integral()==0 : continue
                  cutLabel = myHist.GetXaxis().GetBinLabel(iBin)
                  if not cutLabel : cutLabel = "Cut#"+str(iBin-1)
                  legendEntry = cutLabel + ": " + str(int(projY.Integral(1,projY.GetNbinsX()+1))) + ", avg = " +  str(round(projY.GetMean(),2)) + "#pm" + str(round(projY.GetStdDev(),2))
                  projY.Scale(1/projY.Integral())
                  projY.SetStats(0)
                  colorIdx = (iBin-1) % len(colors)
                  projY.SetLineColor(colors[colorIdx])
                  projY.SetMarkerColor(colors[colorIdx])
                  projY.SetMarkerSize(0.5)
                  projections.append(projY)
                  if len(projections) == 1:
                    projY.Draw("P")
                  else:
                    projY.Draw("SAMEP")
                  projY.GetXaxis().SetRange(1,projY.GetNbinsX()+1)
                  if ("RecoilX" in keyname) :
                    projY.GetXaxis().SetRange(0,projY.GetNbinsX()+1)

                  max = numpy.maximum(max,projY.GetMaximum()*1000)
                  projY.GetYaxis().SetRangeUser(0.0000001,max)
                  projY.GetYaxis().SetTitle("Normalized events / bin")
                  legend.AddEntry(projY,legendEntry,"LP")

                  binWidth = projY.GetXaxis().GetBinWidth(1)
                  overFlowLocXCent = projY.GetXaxis().GetBinCenter(projY.GetNbinsX()+ 1)
                  overFlowLocX = (overFlowLocXCent - (binWidth)/2)

                overFlowLine = ROOT.TLine()
                overFlowLine.SetLineWidth(2)
                overFlowLine.SetLineStyle(ROOT.kDashed)
                legend.Draw("SAME")
                tex5.Draw("SAME")
                overFlowText.Draw("SAME")
                if len(projections) > 0:
                  overFlowLine.DrawLine(overFlowLocX,projections[0].GetMinimum(),overFlowLocX,projections[0].GetMaximum())
                canvas.SaveAs("Compare"+sampleInFile[:-5]+"/"+keyname2+".png")
                
                ROOT.gStyle.SetPadRightMargin(.09)
                ROOT.gStyle.SetPadTopMargin(0.1)
                ROOT.gStyle.SetPadBottomMargin(0.20)
                ROOT.gStyle.SetPadLeftMargin(0.15)
                canvasSCutFlowtring = 'canvasCutFlow'+str(i)
                canvasCutFlow = ROOT.TCanvas(canvasSCutFlowtring, canvasSCutFlowtring, 800,800)
                canvasCutFlow.SetLogy()
                cutflow.LabelsOption("v")
                cutflow.SetStats(0)
                cutflow.Draw("HISTOTEXT45")
                cutflow.GetYaxis().SetTitle("Events / bin")
                cutflow.GetYaxis().SetRangeUser(1,cutflow.GetMaximum()*100)
#                if ("Rev" in keyname) :
##                  cutflow.GetXaxis().SetBinLabel(5,"E_{cell,max} < 300")
#                  cutflow.GetXaxis().SetBinLabel(12,"Non-fiducial")
#                else:
##                  cutflow.GetXaxis().SetBinLabel(10,"E_{cell,max} < 300")
                # cutflow.GetXaxis().SetBinLabel(2,"Non-fiducial")
                # cutflow.GetXaxis().SetBinLabel(3,"Triggerred")
                tex5.Draw("SAME")
                tex2.Draw("SAME")
                tex3.Draw("SAME")
                tex4.Draw("SAME")

                canvasCutFlow.SaveAs("Compare"+sampleInFile[:-5]+"/CutFlow_"+keyname2+".png")

                canvasCutFlowNstring = 'canvasCutFlowN'+str(i)
                canvasCutFlowN = ROOT.TCanvas(canvasCutFlowNstring, canvasCutFlowNstring, 800,800)
                cutflow.SetStats(0)
                if (cutflow.GetBinContent(1)>0) : cutflow.Scale(1/cutflow.GetBinContent(1))
                cutflow.Draw("HISTOTEXT45")
                cutflow.GetYaxis().SetTitle("Efficiency")
#                if ("Rev" in keyname) :
##                  cutflow.GetXaxis().SetBinLabel(5,"E_{cell,max} < 300")
#                  cutflow.GetXaxis().SetBinLabel(12,"Non-fiducial")
#                else:
##                  cutflow.GetXaxis().SetBinLabel(10,"E_{cell,max} < 300")
#                  cutflow.GetXaxis().SetBinLabel(3,"Non-fiducial")
                cutflow.LabelsOption("v")
                tex2.Draw("SAME")
                tex3.Draw("SAME")
                tex4.Draw("SAME")
                tex5.Draw("SAME")
                canvasCutFlowN.SaveAs("Compare"+sampleInFile[:-5]+"/CutFlowNorm_"+keyname2+".png")
