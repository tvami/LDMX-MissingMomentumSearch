# POD: few jobs, long wall time. Defaults are -n 16 -f 210 => one SLURM job
# per sample directory below (3360 files of capacity per job).
# Inputs are the reco_dropsim *event* files; the *_histo.root reco DQM files in
# the same directories are excluded by the submitter's default -g '*_reco.root'.

python3 submit_pod_mt_input.py -py cfg_ana_cutBasedDM_v15.py -i /home/vamitamas/Samples8GeV/reco_dropsim/ecal_pn_v15_8gev

python3 submit_pod_mt_input.py -py cfg_ana_cutBasedDM_v15.py -i /home/vamitamas/Samples8GeV/reco_dropsim/ecal_pn_v15_8gev_batch1p5

python3 submit_pod_mt_input.py -py cfg_ana_cutBasedDM_v15.py -i /home/vamitamas/Samples8GeV/reco_dropsim/ecal_pn_v15_8gev_batch2

python3 submit_pod_mt_input.py -py cfg_ana_cutBasedDM_v15.py -i /home/vamitamas/Samples8GeV/reco_dropsim/ecal_pn_v15_8gev_batch3
