#!/bin/bash
# hadd the per-file CutBasedDM histograms into one file per sample.
# Batched because ecal_pn alone is ~6k files, past what one hadd command can take
# on argv, and -j keeps it from being the slow step.
export PATH=/sdf/home/t/tamasvami/.local/bin:$PATH
cd /sdf/group/ldmx/users/tamasvami/ldmx-analysis/v4.9.2/ldmx-sw/LDMX-MissingMomentumSearch || exit 1
A=analysis
mkdir -p $A/tmp

hadd_sample () {   # $1 = subdir under analysis/, $2 = output stem
  local sub=$1 stem=$2
  local list=$A/tmp/${stem}.list
  find $A/$sub -maxdepth 1 -name '*_histo.root' -size +0 2>/dev/null | sort > $list
  local n=$(wc -l < $list)
  if [ "$n" -eq 0 ]; then echo "  $stem: no inputs, skipped"; return; fi
  rm -f $A/${stem}_histos.root
  if [ "$n" -le 400 ]; then
    denv hadd -f -j 8 $A/${stem}_histos.root @$list >/dev/null 2>$A/tmp/${stem}.err || echo "  $stem: HADD FAILED, see $A/tmp/${stem}.err"
  else
    # two-stage: chunks of 400, then merge the chunks
    rm -rf $A/tmp/$stem; mkdir -p $A/tmp/$stem
    split -l 400 -d -a 4 $list $A/tmp/$stem/part_
    for part in $A/tmp/$stem/part_*; do
      denv hadd -f -j 8 ${part}.root @${part} >/dev/null 2>&1
    done
    denv hadd -f -j 8 $A/${stem}_histos.root $A/tmp/$stem/part_*.root >/dev/null 2>$A/tmp/${stem}.err || echo "  $stem: HADD FAILED, see $A/tmp/${stem}.err"
  fi
  echo "  $stem: merged $n files -> $A/${stem}_histos.root"
}

# two names per signal mass: the <mass> form the table script wants, and a
# signal_mass_<X>MeV form, because compareWithArguementList2D.py builds its
# legend from substrings of the filename ("1MeV", "10MeV", ...)
for m in 1.0 0.1 0.01 0.001 ; do
  hadd_sample signal_v15_8gev/$m signal_v15_8gev_$m
done
declare -A MEV=( [0.001]=1 [0.01]=10 [0.1]=100 [1.0]=1000 )
for m in 0.001 0.01 0.1 1.0 ; do
  src=analysis/signal_v15_8gev_${m}_histos.root
  dst=analysis/signal_mass_${MEV[$m]}MeV_v15_8GeV_histos.root
  [ -f "$src" ] && cp -f "$src" "$dst" && echo "  also as $(basename $dst)"
done
for s in target_pn_v15_8gev target_conversion_v15_8gev \
         ecal_conversion_v15_8gev ecal_pn_v15_8gev ; do
  hadd_sample $s $s
done
