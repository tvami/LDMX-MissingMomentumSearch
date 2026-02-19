#!/usr/bin/env python
import argparse
import glob
import logging
import os
import subprocess
import time
from datetime import datetime

# How to run example:
# python3 submit_sdf_mt_input.py -py my_config.py -i /path/to/input/dir

# TODO: Take the last bit of the --indir path and keep that string in the filelists

def main():
    parser = argparse.ArgumentParser(description='Submit parallel batch jobs on SDF with input files')
    parser.add_argument('-py', '--script', action='store', dest='script', required=True)
    parser.add_argument('-i', '--indir', action='store', dest='indir', required=True)
    parser.add_argument('-t', '--test', action='store_true', dest='test')
    parser.add_argument('-n', '--nparallel', action='store', dest='nparallel', type=int, default=8,
                        help='Number of parallel tasks per SLURM job (default: 8)')
    parser.add_argument('-f', '--files-per-task', action='store', dest='files_per_task', type=int, default=40,
                        help='Number of input files per parallel task (default: 40)')
    args = parser.parse_args()

    logging.basicConfig(format='[ submitJobs ][ %(levelname)s ]: %(message)s', level=logging.DEBUG)

    input_files = sorted(glob.glob(args.indir + "/*.root"))
    if not input_files:
        logging.error('No .root files found in %s' % args.indir)
        return

    logging.info('Found %d input files' % len(input_files))

    # SDF paths
    jobdir = '/sdf/home/t/tamasvami/slurm/jobs/'
    logdir = '/sdf/home/t/tamasvami/slurm/logs/'
    filelistdir = '/sdf/home/t/tamasvami/slurm/filelists/'+str(args.indir.split('/')[-1])+'/'
    for d in [jobdir, logdir, filelistdir]:
        if not os.path.exists(d):
            logging.info('Creating directory: %s' % d)
            os.makedirs(d)

    # Skip files already present in existing filelists
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

    batch_command = 'sbatch -p roma'
    current_directory = os.getcwd()
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Each SLURM job runs nparallel tasks, each processing files_per_task files
    files_per_job = args.nparallel * args.files_per_task
    num_jobs = (len(input_files) + files_per_job - 1) // files_per_job

    logging.info('Submitting %d SLURM jobs (%d parallel tasks x %d files = %d files per job)'
                 % (num_jobs, args.nparallel, args.files_per_task, files_per_job))

    for job in range(num_jobs):
        job_files = input_files[job * files_per_job : (job + 1) * files_per_job]

        # Split into nparallel chunks and write a file list for each
        filelist_paths = []
        for task in range(args.nparallel):
            task_files = job_files[task * args.files_per_task : (task + 1) * args.files_per_task]
            if not task_files:
                break
            filelist_path = '%sfilelist_%s_job%d_task%d.txt' % (filelistdir, current_time, job, task)
            with open(filelist_path, 'w') as fl:
                fl.write(' '.join(task_files))
            filelist_paths.append(filelist_path)

        if not filelist_paths:
            continue

        # Build the fire-parallel command: each filelist path is one parallel argument
        ntasks = len(filelist_paths)
        command = 'cd %s && just fire-parallel %s {} ::: %s' % (
            current_directory, args.script, ' '.join(filelist_paths))

        job_file = '%s/slurm_submit_%d_%s.job' % (jobdir, job, current_time)
        with open(job_file, 'w') as f:
            f.write('#!/bin/bash\n\n')
            f.write('#SBATCH --partition=roma\n')
            f.write('#SBATCH --account=ldmx\n')
            f.write('#SBATCH --nodes=1\n')
            f.write('#SBATCH --ntasks-per-node=%d\n' % ntasks)
            f.write('#SBATCH --ntasks=%d\n' % ntasks)
            f.write('#SBATCH --cpus-per-task=1\n')
            f.write('#SBATCH --mem=16000M\n')
            f.write('#SBATCH --error=%s/slurm-%%A_%%a.err\n' % logdir)
            f.write('#SBATCH --output=%s/slurm-%%A_%%a.out\n' % logdir)
            f.write('#SBATCH --time=62:05:00\n')
            f.write('#SBATCH --mail-type=FAIL\n')
            f.write('#SBATCH --mail-user=tamasvami@ucsb.edu\n\n')
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
