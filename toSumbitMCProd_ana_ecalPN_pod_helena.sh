# Same as toSumbitMCProd_ana_ecalPN_pod.sh but with the helena.onnx ECal veto.
# -T helena keeps the filelists separate from the segmip production so the
# already-processed skip logic does not confuse the two versions.
# Output goes to ./analysis_helena/<sample>/ .

python3 submit_pod_mt_input.py -py cfg_ana_cutBasedDM_v15_helena.py -T helena -i /home/vamitamas/Samples8GeV/reco_dropsim/ecal_pn_v15_8gev

python3 submit_pod_mt_input.py -py cfg_ana_cutBasedDM_v15_helena.py -T helena -i /home/vamitamas/Samples8GeV/reco_dropsim/ecal_pn_v15_8gev_batch1p5

python3 submit_pod_mt_input.py -py cfg_ana_cutBasedDM_v15_helena.py -T helena -i /home/vamitamas/Samples8GeV/reco_dropsim/ecal_pn_v15_8gev_batch2

python3 submit_pod_mt_input.py -py cfg_ana_cutBasedDM_v15_helena.py -T helena -i /home/vamitamas/Samples8GeV/reco_dropsim/ecal_pn_v15_8gev_batch3
