#!/bin/bash
# Render the cut-and-count / PNet talk plots, one square plot per figure.
#
#   denv bash make_talk_plots.sh [bkg_mode] [stamps] [out_dir]
#
# bkg_mode: how the four backgrounds are drawn.
#             mixed (default)  ECal PN a grey band, the other three coloured
#             color            all four coloured
#             shade            a grey ramp
#             hatch            neutral fills at different hatch angles
#             point            no fill, the reference's markers
# stamps:   stamps (default) | nostamps, to drop the LDMX / Simulation / EoT
#           stamps when something else on the slide carries them.
# out_dir defaults to style_test/<mode>, INSIDE the ldmx-sw tree: denv mounts
# only that read-write, so the talk directory cannot be written from inside the
# container. Copy the results over from the host afterwards.
set -u
cd "$(dirname "$0")"
m=${1:-mixed}
s=${2:-stamps}
out=${3:-style_test/$m}
mkdir -p "$out"
python3 plot_cnc_vars.py analysis_pnetv11 "$out" "$m" "$s"
python3 plot_pnet_disc.py analysis_pnetv11 "$out" "$m"
ls -l "$out"
