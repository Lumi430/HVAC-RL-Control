from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from xml.dom.minidom import parseString

import requests
import pandas as pd
import os, shutil, subprocess, json, socket, ast

this_dir_path = os.path.dirname(os.path.realpath(__file__))

# Create your views here.
def index(request):
	run_dirs_names, run_dirs = getRuns();
	return render(request, 'interface_v1/html/srtdash/index.html',\
    	{'run_dirs_names': run_dirs_names})


def getRuns():
	scan_dir = this_dir_path + '/../../src/';
	dirs = os.listdir(scan_dir);
	run_dirs_names = [];
	run_dirs = []
	for this_dir in dirs:
		if 'run' in this_dir and os.path.isdir(scan_dir + this_dir):
			run_dirs_names.append(this_dir);
			run_dirs.append(scan_dir + this_dir)
	return run_dirs_names, run_dirs;

def get_worker_status(request):
	"""
	Args:
		arguments: str
			In the pattern "ip=0.0.0.0&port=9999"
	"""
	ip = request.GET.get('ip')
	port = int(request.GET.get('port'))
	# Create a socket
	s = socket.socket();
	s.connect((ip, port));
	s.sendall(b'getstatus');
	recv_str = s.recv(1024).decode(encoding = 'utf-8');
	recv_list = ast.literal_eval(recv_str)
	recv_json = {};
	recv_json['cpu'] = recv_list[1]
	recv_json['mem'] = recv_list[2]
	recv_json['running'] = recv_list[3]
	recv_json['queue'] = recv_list[4]
	recv_json['steps'] = recv_list[5]

	return JsonResponse(recv_json, json_dumps_params={'indent': 2})



def get_all_exp(request, run_name):
	run_dirs_names, run_dirs = getRuns();
	run_dir_this = run_dirs[run_dirs_names.index(run_name)]
	run_this_exp_dirs = os.listdir(run_dir_this);
	pd_list = [];
	for run_this_exp_dir in run_this_exp_dirs:
		run_this_exp_full_dir = run_dir_this + os.sep + run_this_exp_dir
		if os.path.isdir(run_this_exp_full_dir):
			if os.path.isfile(run_this_exp_full_dir + '/run.sh'):
				if not os.path.isfile(run_this_exp_full_dir + '/args.csv'):
					with open(run_this_exp_full_dir + '/run.sh', 'r') as ext_run_f:
						ext_run_f_lines = ext_run_f.read().splitlines()
					ext_run_f_lines[-1] += ' --check_args_only True';
					with open(run_this_exp_full_dir + '/~run.sh', 'w') as temp_run_f:
						[temp_run_f.write('%s\n'%line) for line in ext_run_f_lines]
					subprocess.call('bash ' + run_this_exp_full_dir + '/~run.sh', shell=True,
									cwd = run_this_exp_full_dir)
				this_exp_pd = pd.read_csv(run_this_exp_full_dir + '/args.csv');
				this_exp_pd['exp_id'] = pd.Series([int(run_this_exp_dir)]);
				this_exp_status, this_exp_machine = check_exp_status(run_this_exp_full_dir, 
												   int(this_exp_pd.iloc[0]['max_interactions']));
				this_exp_pd.insert(0, 'machine', this_exp_machine)
				this_exp_pd.insert(0, 'status', this_exp_status)
				pd_list.append(this_exp_pd);
			else:
				pass;
	all_exp_args_pd = pd.concat(pd_list, sort = False);
	all_exp_args_pd.set_index('exp_id', drop = True, inplace = True);
	all_exp_args_pd.sort_index(axis=0, inplace = True);
	response_html = all_exp_args_pd.to_html(bold_rows = True, table_id = 'runs_args_tb');

	# add ids to the html
	def add_id_to_html(response_html, table_cols):
		dom = parseString(response_html);
		tbody = dom.getElementsByTagName('tbody')[0];
		trs = tbody.getElementsByTagName('tr');
		for tr in trs:
			th = tr.getElementsByTagName('th')[0];
			tr_id = th.firstChild.data;
			tr.setAttribute('id', ':'.join([run_name, tr_id]));
			tds = tr.getElementsByTagName('td');
			for i in range(len(tds)):
				td = tds[i];
				td.setAttribute('id', ':'.join([run_name, tr_id, table_cols[i]]))
		return dom.toxml();
	table_col_names = all_exp_args_pd.columns.values;
	response_html = add_id_to_html(response_html, table_col_names);
	return HttpResponse(response_html)


def check_exp_status(exp_full_dir, itrct_num_total):
	eval_res_hist_dir = exp_full_dir + '/eval_res_hist.csv';
	meta_dir = exp_full_dir + '/run.meta';
	itrct_num_now = None;
	meta_run_status = None;
	meta_run_machine = None;
	exp_status = None;
	
	if os.path.isfile(eval_res_hist_dir):
		with open(eval_res_hist_dir, 'r') as eval_res_his_f:
			eval_res_his_f_lines = eval_res_his_f.read().splitlines()
		itrct_num_now = int(float(eval_res_his_f_lines[-1].split(',')[0]))
	if os.path.isfile(meta_dir):
		with open(meta_dir, 'r') as meta_dir_f:
			meta_dir_f_json = json.load(meta_dir_f)
		meta_run_status = meta_dir_f_json['status']
		meta_run_machine = meta_dir_f_json['machine'];
	if itrct_num_now == itrct_num_total and meta_run_status == 'complete':
		exp_status = 'complete';
	elif itrct_num_now == None and meta_run_status == None:
		exp_status = 'not started';
	elif not meta_run_status == None:
		exp_status = meta_run_status;
	else:
		exp_status = 'undefined';
	return (exp_status, meta_run_machine);











