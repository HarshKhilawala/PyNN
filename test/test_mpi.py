"""
Test that running a distributed simulation using MPI gives the same results
as a local, serial simulation.
"""

import os
from subprocess import Popen, PIPE, STDOUT
import tempfile
import shutil
import re
import sys
import time

usage = "python test_mpi.py <script> <simulator> <num_processes>"

if len(sys.argv) < 4:
    print usage
    sys.exit(1)

script = sys.argv[1] #"../examples/simpleRandomNetwork.py"
simulator = sys.argv[2] #"nest"
n = int(sys.argv[3]) #2
script_args = " ".join(sys.argv[4:])


# === Run simulations ==========================================================

tmpdirs = {'serial': tempfile.mkdtemp(),
           'distrib': tempfile.mkdtemp()}

os.mkdir("%s/Results" % tmpdirs['serial'])
Popen("mpiexec -n %d mkdir -p %s/Results" % (n, tmpdirs['distrib']), shell=True).wait()

job1 = Popen("python %s %s %s" % (os.path.abspath(script), simulator, script_args),
             stdin=None, stdout=None, stderr=STDOUT, shell=True, cwd=tmpdirs['serial'])
job2 = Popen("mpiexec -n %d -wdir %s python %s %s %s" % (n, tmpdirs['distrib'],
                                                      os.path.abspath(script),
                                                      simulator, script_args),
             stdin=None, stdout=None, stderr=STDOUT, shell=True, cwd=tmpdirs['distrib'])
job2.wait()
job1.wait()


# === Compare output files =====================================================
print "="*80

def find_files(path):
    data_files = []
    for root, dirs, files in os.walk(path):
        #print root, dirs, files
        for file in files:
            if ".log" in file:
                continue
            full_path = os.path.join(root, file)
            rel_path = full_path[len(path)+1:]
            data_files.append(rel_path)
    return data_files

def clean_up():
    shutil.rmtree(tmpdirs['serial'])
    Popen("mpiexec -n %d rm -rf %s" % (n, tmpdirs['distrib']), shell=True).wait()

def fail(msg):
    print "\nFAIL:", msg
    print "\nCommand to remove temporary files: rm -rf %s %s" % tuple(tmpdirs.values())
    sys.exit(1)

# Find output files
output_files = {'serial': find_files(tmpdirs['serial']),
                'distrib': find_files(tmpdirs['distrib'])}

# The filenames may have information about the number of processes, which we
# wish to ignore for the purposes of comparing filenames.
np_pattern = re.compile(r'_np\d+')
filename_maps = {'serial':{}, 'distrib': {}}
for mode in 'serial', 'distrib':
    for filename in output_files[mode]:
        filename_maps[mode][np_pattern.sub("", filename)] = os.path.join(tmpdirs[mode], filename)

# Check that the filenames match
serial_names = filename_maps['serial'].keys()
distrib_names = filename_maps['distrib'].keys()
serial_names.sort()
distrib_names.sort()
names_match = serial_names == distrib_names
if not names_match:
    fail("File names do not match:\n  Serial: %s\n  Distributed: %s" % ("\n    ".join(serial_names),
                                                                        "\n    ".join(distrib_names))
        )

# Check that the file sizes match
file_sizes = dict.fromkeys(filename_maps, {})
for name in filename_maps['serial']:
    for mode in 'serial', 'distrib':
        file_sizes[mode][name] = os.stat(filename_maps[mode][name]).st_size

print "Output files" + " "*44 + "serial     distrib"
for name in filename_maps['serial']:
    print "  %-50s %9s   %9s" % (name, file_sizes['serial'][name], file_sizes['distrib'][name])

sizes_match = file_sizes['serial'] == file_sizes['distrib']
if not sizes_match:
    fail("File sizes do not match.")

# Sort the files
jobs = []
for mode in 'serial', 'distrib':
    for filename in filename_maps[mode].values():
        cmd = "sort %s > %s,sorted" % (filename, filename)
        jobs.append(Popen(cmd, shell=True))
for job in jobs:
    job.wait()

# Check that the sorted file contents match    
diffs = {}
for name in filename_maps['serial']:
    diffs[name] = open("%s,sorted" % filename_maps['serial'][name]).read() == open("%s,sorted" % filename_maps['distrib'][name]).read()
    
if not all(diffs.values()):
    fail("the following files are different:\n  " + \
         "\n  ".join("%s -- %s" % (filename_maps['serial'][name], filename_maps['distrib'][name]) for name,same in diffs.items() if not same)
        )

# If everything worked...
print "PASS: the serial and distributed simulations give identical results"
clean_up()