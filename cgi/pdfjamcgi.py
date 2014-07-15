#!/usr/bin/python

# PDFjam CGI interface.
# Written by Ilya Zverev, licensed WTFPL.

import os, sys, cgi, re
import tempfile, subprocess, shutil
import cgitb
cgitb.enable()

PDFTK = '/usr/bin/pdftk'
PDFJAM = '/usr/bin/pdfjam'
PDFTK_NEW = False # set to True for pdftk 1.45+

def remove_files(fp):
	if type(fp) is list:
		for fp1 in fp:
			remove_files(fp1)
	elif type(fp) is dict:
		for fp1 in fp.values():
			remove_files(fp1)
	elif type(fp) is str:
		try:
			os.remove(fp)
		except OSError:
			pass
	elif hasattr(fp, 'read') and hasattr(fp, 'name'):
		try:
			os.remove(fp.name)
		except OSError:
			pass

def error_die(msg):
	print 'Content-Type: text/plain; charset=utf-8'
	print ''
	print 'Error: {}.'.format(msg);
	sys.exit(1)

class MyFieldStorage(cgi.FieldStorage):
	def make_file(self, binary=None):
		return tempfile.NamedTemporaryFile('wb+', delete=False, suffix='.pdf')

form = MyFieldStorage()

pdf = {}
for p in 'abcd':
	key = 'pdf'+p
	if key in form and form[key].file and form[key].filename:
		if hasattr(form[key].file, 'name'):
			pdf[p.upper()] = form[key].file
		else:
			# for some reason small files are not make_file'd
			fp = tempfile.NamedTemporaryFile('wb+', delete=False, suffix='.pdf')
			fp.write(form[key].value)
			fp.close()
			pdf[p.upper()] = fp

if not len(pdf):
	error_die('At least one PDF file parameter is required')

if len(pdf) == 1 and len(form.getfirst('pdftk', '')) < 2:
	# only one file, no need to run pdftk
	tmpName = pdf.values()[0].name
else:
	# process files with pdftk
	pages = form.getfirst('pdftk', '').strip().upper()
	if not len(pages):
		pages = ' '.join(sorted(pdf.keys()))
	elif not re.match('^[A-D][1-9A-Z-]*(?: +[A-D][1-9A-Z-]*)*$', pages):
		remove_files(pdf)
		error_die('Incorrect pages format: {}'.format(pages))
	
	if PDFTK_NEW:
		# replace rotation values with new
		rotation = { 'W': 'west', 'E': 'east', 'S': 'south', 'L': 'left', 'R': 'right', 'D': 'down', 'N': 'north' }
		def fix_rot(page):
			for k, v in rotation.items():
				if page.endswith(k):
					return page[:-1] + v
			return page
		pages = ' '.join([fix_rot(page) for page in re.split('\s+', pages)])

	tmpfile, tmpName = tempfile.mkstemp(suffix='.pdf')
	command = [PDFTK]
	command.extend(['{}={}'.format(k, v.name) for k, v in pdf.items()])
	command.append('cat')
	command.extend(re.split('\s+', pages))
	command.extend(['output', tmpName])
	process = subprocess.Popen(command, stderr=subprocess.PIPE)
	_, err = process.communicate()
	result = process.returncode
	remove_files(pdf)
	if result != 0 or not os.path.isfile(tmpName) or os.stat(tmpName).st_size == 0:
		remove_files(tmpName)
		error_die('PDFtk returned error code {}\n\n{}'.format(result, err))

# now process result with pdfjam
outfile, outputName = tempfile.mkstemp()
command = [PDFJAM, tmpName, '--nup', '2x1', '--landscape', '--a4paper', '--outfile', outputName]
process = subprocess.Popen(command, stderr=subprocess.PIPE)
_, err = process.communicate()
result = process.returncode
remove_files(tmpName)
if result != 0:
	error_die('PDFjam returned error code {}\n\n{}'.format(result, err))

length = os.stat(outputName).st_size
if length == 0:
	remove_files(outputName)
	error_die('Resulting PDF is empty for some reason')

print 'Content-Type: application/pdf'
print 'Content-Disposition: attachment; filename=pdfjam-result.pdf'
print 'Content-Length: {}'.format(length)
print ''
with open(outputName, 'rb') as f:
	shutil.copyfileobj(f, sys.stdout)

remove_files(outputName)
