#!/bin/bash
# usage: denv ./strip_one.sh <in.root> <out.root>
exec root -l -b -q "/home/vamitamas/ldmx-analysis/v4.8.3/ldmx-sw/strip_signal.C(\"$1\",\"$2\")"
