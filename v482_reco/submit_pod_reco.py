#!/usr/bin/env python
import argparse
import glob
import logging
import os
import subprocess
import time
from datetime import datetime

# POD submitter for the v4.8.2 reco re-run over the preselection skims.
#
# How to run:
#   cd /home/vamitamas/ldmx-analysis/v4.8.2/ldmx-sw
#   python3 submit_pod_reco.py -py cfg_reco_dropsim_segmip.py -T v482segmip \
#       -i /home/vamitamas/Samples8GeV/pres_skim/ecal_pn_v15_8gev_batch2
#
# This directory IS the denv workspace, so plain `just fire-parallel` works
# (unlike the CutBasedDM repo, which needs `just -f <ldmx-sw>/justfile`).
#
# A filelist must not mix samples: the config derives the output directory from
# the parent directory of the LAST file in the list.


def main():
    parser = argparse.ArgumentParser(description='Submit v4.8.2 reco jobs on POD')
    parser.add_argument('-py', '--script', action='store', dest='script', required=True)
    parser.add_argument('-i', '--indir', action='store', dest='indir', required=True)
    parser.add_argument('-t', '--test', action='store_true', dest='test')
    # POD: long wall times are fine, keep the job count small.
    parser.add_argument('-n', '--nparallel', action='store', dest='nparallel', type=int, default=16,
                        help='Number of parallel tasks per SLURM job (default: 16)')
    parser.add_argument('-f', '--files-per-task', action='store', dest='files_per_task', type=int, default=20,
                        help='Number of input files per parallel task (default: 20)')
    parser.add_argument('-g', '--glob', action='store', dest='pattern', default='*_pres.root',
                        help="Input file pattern inside --indir (default: '*_pres.root')")
    parser.add_argument('-m', '--mem', action='store', dest='mem', default='64000M',
                        help='SLURM --mem per node (default: 64000M; reco+tracking is heavy)')
    parser.add_argument('-T', '--tag', action='store', dest='tag', default='v482reco',
                        help="Tag separating filelist dirs between variants (default: 'v482reco')")
    parser.add_argument('--no-skip', action='store_true', dest='no_skip',
                        help='Process all input files, ignoring existing filelists')
    args = parser.parse_args()

    logging.basicConfig(format='[ submitJobs ][ %(levelname)s ]: %(message)s', level=logging.DEBUG)

    input_files = sorted(glob.glob(os.path.join(args.indir, args.pattern)))
    if not input_files:
        logging.error('No files matching %s found in %s' % (args.pattern, args.indir))
        return

    logging.info('Found %d input files' % len(input_files))

    jobdir = '/home/vamitamas/slurm/jobs/'
    logdir = '/home/vamitamas/slurm/logs/'
    # read INSIDE denv -> must live under a denv-mounted path
    filelistdir = ('/home/vamitamas/Samples8GeV/slurm_filelists/' + args.tag + '_'
                   + str(args.indir.rstrip('/').split('/')[-1]) + '/')
    for d in [jobdir, logdir, filelistdir]:
        if not os.path.exists(d):
            logging.info('Creating directory: %s' % d)
            os.makedirs(d)

    if not args.no_skip:
        already_processed = set()
        for fl_path in glob.glob(filelistdir + '*.txt'):
            with open(fl_path) as fl:
                already_processed.update(os.path.basename(p) for p in fl.read().split())
        if already_processed:
            before = len(input_files)
            input_files = [f for f in input_files if os.path.basename(f) not in already_processed]
            logging.info('Skipped %d already-listed files, %d new files to process'
                         % (before - len(input_files), len(input_files)))
        if not input_files:
            logging.info('No new files to process — all files already in filelists.')
            return
    else:
        logging.info('Skipping filelist check (--no-skip)')

    batch_command = 'sbatch -p batch'
    current_directory = os.getcwd()
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")

    files_per_job = args.nparallel * args.files_per_task
    num_jobs = (len(input_files) + files_per_job - 1) // files_per_job

    logging.info('Submitting %d SLURM jobs (%d parallel tasks x %d files = %d files per job)'
                 % (num_jobs, args.nparallel, args.files_per_task, files_per_job))

    for job in range(num_jobs):
        job_files = input_files[job * files_per_job: (job + 1) * files_per_job]

        filelist_paths = []
        for task in range(args.nparallel):
            task_files = job_files[task * args.files_per_task: (task + 1) * args.files_per_task]
            if not task_files:
                break
            filelist_path = '%sfilelist_%s_job%d_task%d.txt' % (filelistdir, current_time, job, task)
            with open(filelist_path, 'w') as fl:
                fl.write(' '.join(task_files))
            filelist_paths.append(filelist_path)

        if not filelist_paths:
            continue

        ntasks = len(filelist_paths)
        command = 'cd %s && just fire-parallel %s {} ::: %s' % (
            current_directory, args.script, ' '.join(filelist_paths))

        job_file = '%s/slurm_submit_%s_%d_%s.job' % (jobdir, args.tag, job, current_time)
        with open(job_file, 'w') as f:
            f.write('#!/bin/bash\n\n')
            f.write('#SBATCH --partition=batch\n')
            f.write('#SBATCH --nodes=1\n')
            f.write('#SBATCH --ntasks-per-node=%d\n' % ntasks)
            f.write('#SBATCH --ntasks=%d\n' % ntasks)
            f.write('#SBATCH --cpus-per-task=1\n')
            f.write('#SBATCH --mem=%s\n' % args.mem)
            f.write('#SBATCH --error=%s/slurm-%%A_%%a.err\n' % logdir)
            f.write('#SBATCH --output=%s/slurm-%%A_%%a.out\n' % logdir)
            f.write('#SBATCH --time=120:05:00\n')
            f.write('#SBATCH --mail-type=FAIL\n')
            f.write('#SBATCH --mail-user=tamasvami@ucsb.edu\n\n')
            f.write('export PATH="$HOME/.local/bin:$PATH"\n\n')
            f.write('cd $SLURM_SUBMIT_DIR\n\n')
            f.write('/bin/hostname\n\n')
            f.write('%s\n' % command)

        submit_command = '%s %s' % (batch_command, job_file)
        logging.info('Job %d: %d tasks, %d total files' % (job, ntasks, len(job_files)))
        logging.info('Job submit command: %s' % submit_command)

        if args.test:
            logging.info('Test mode - not submitting.')
            print(command)
        else:
            subprocess.Popen(submit_command, shell=True).wait()
            time.sleep(3)


if __name__ == "__main__":
    main()
