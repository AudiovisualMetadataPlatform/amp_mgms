import sys, subprocess, os

kaldi_dir = sys.argv[1]
expt_results_dir = sys.argv[2]
ref_fpath = sys.argv[2]
expt_name = os.path.basename(expt_results_dir)

print 'Prepping sclite...'

if not os.path.exists(expt_results_dir):
	os.mkdir(expt_results_dir)

os.chdir(expt_results_dir)
hyp_path = '{}_temp.hyp'.format(expt_name)
with open(hyp_path, 'w') as hypfile:
	hyp_list = []
	for f in os.listdir(kaldi_dir):
		fpath = os.path.join(kaldi_dir, f)
		with open(fpath) as transcript:
			trs_text = transcript.read().lower().strip()
			idname = ' ({}-1)'.format(f[:-4])
			trs_text += idname
			hyp_list.append(trs_text)
		hyp_str = '\n'.join(hyp_list)
	hypfile.write(hyp_str)
	hypfile.write('\n')

final_hyp_path = '{}.hyp'.format(expt_name)
os.system("cat {} | tr -d '.' > {}".format(hyp_path, final_hyp_path))

print 'Running sclite...'
os.system('sclite -r {0} -h {1}.hyp -n {1} -i rm -o dtl pra sum'.format(ref_fpath, expt_name))