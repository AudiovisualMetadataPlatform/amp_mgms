import os, sys, subprocess, json2txt

expt_dir = sys.argv[1] #where experiment kaldi setup is stored, incl local scripts
wav_dir = sys.argv[2]
expt_name = os.path.basename(expt_dir)

if len(sys.argv) != 3:
	print 'USAGE: run_kaldi.py <expt_dir> <wav_dir>'

os.chdir(expt_dir)
print 'Entering experiment dir. Validating...'
expected = ['exp', 'run.sh', 'scripts', 'steps', 'tools', 'utils']
for p in expected:
	if not os.path.exists(p):
		raise Exception('Invalid experiment setup. Required: exp, run.sh, scripts, steps, tools, utils')
print 'Valid experiment dir'

print "Experiment directory (cwd): ", expt_dir 
print "Wav dir: ", wav_dir

# print 'Running kaldi on each file'
#run kaldi and convert output to txt file
for f in os.listdir(wav_dir):
	print "Processing file ", f
	f_base = f[:-4]
	json_file = "/writable/output/" + f_base + ".json"
	txt_file = "/writable/output/" + f_base + ".txt"
	# call kaldi
	subprocess.call(["./run.sh", wav_dir + "/" + f, json_file])
	# create text file
	json2txt.convert(json_file, txt_file)
	
