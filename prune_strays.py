#!/usr/bin/env python3
"""Delete histogram files that are not the expected output of a chunk.

Interactive unit tests write into the same analysis/<sample>/ tree, named after
whatever single file they were given. Those events are also covered by a real
chunk, so leaving them in place double counts them in the hadd.

Usage: prune_strays.py <sample> <files_per_task> [--apply]
"""
import glob
import os
import sys

RECO = '/sdf/data/ldmx/private_production/mc26/reco_v492/'
ANA = 'analysis/'


def main():
    sample, per_task = sys.argv[1], int(sys.argv[2])
    apply_ = '--apply' in sys.argv

    files = sorted(glob.glob(RECO + sample + '/*_reco.root'))
    expected = set()
    for i in range(0, len(files), per_task):
        chunk = files[i:i + per_task]
        expected.add(os.path.basename(chunk[-1])[:-5] + '_histo.root')

    strays = []
    for p in sorted(glob.glob(os.path.join(ANA, sample, '*_histo.root'))):
        if os.path.basename(p) not in expected:
            strays.append(p)

    for p in strays:
        print('stray: %s' % p)
        if apply_:
            os.remove(p)
    sys.stderr.write('%s: %d expected, %d strays%s\n'
                     % (sample, len(expected), len(strays),
                        ' (removed)' if apply_ else ' (dry run)'))


if __name__ == '__main__':
    main()
