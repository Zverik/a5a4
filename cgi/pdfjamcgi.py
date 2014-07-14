#!/usr/bin/python

# PDFjam CGI interface.
# Written by Ilya Zverev, licensed WTFPL.

import os, sys, cgi, re
import tempfile, subprocess, shutil
import cgitb
cgitb.enable()

PDFTK = '/usr/bin/pdftk'
PDFJAM = '/usr/bin/pdfjam'

def close_files(files):
	for fp in files:
		try:
			if type(fp) is str:
				os.remove(fp)
			elif type(fp) is tempfile.NamedTemporaryFile:
				os.remove(fp.name)
			elif type(fp) is list:
				close_files(fp)
			elif type(fp) is dict:
				close_files(fp.values())
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
	pages = form.getfirst('pdftk', '').strip()
	if not len(pages):
		pages = ' '.join(sorted(pdf.keys()))
	elif not re.match('^[A-D][1-9A-Z-]*(?: +[A-D][1-9A-Z-]*)*$', pages):
		close_files(pdf.values())
		error_die('Incorrect pages format: {}'.format(pages))

	tmpfile, tmpName = tempfile.mkstemp(suffix='.pdf')
	command = [PDFTK]
	command.extend(['{}={}'.format(k, v.name) for k, v in pdf.items()])
	command.append('cat')
	command.extend(re.split('\s+', pages))
	command.extend(['output', tmpName])
	process = subprocess.Popen(command, stderr=subprocess.PIPE)
	_, err = process.communicate()
	result = process.returncode
	if result != 0 or not os.path.isfile(tmpName) or os.stat(tmpName).st_size == 0:
		close_files([pdf, tmpName])
		error_die('PDFtk returned error code {}\n\n{}'.format(result, err))

# now process result with pdfjam
outfile, outputName = tempfile.mkstemp()
command = [PDFJAM, tmpName, '--nup', '2x1', '--landscape', '--a4paper', '--outfile', outputName]
process = subprocess.Popen(command, stderr=subprocess.PIPE)
_, err = process.communicate()
result = process.returncode
if result != 0:
	close_files([pdf, tmpName])
	error_die('PDFjam returned error code {}\n\n{}'.format(result, err))

os.remove(tmpName)
length = os.stat(outputName).st_size
if length == 0:
	close_files([pdf, outputName])
	error_die('Resulting PDF is empty for some reason')

print 'Content-Type: application/pdf'
print 'Content-Disposition: attachment; filename=pdfjam-result.pdf'
print 'Content-Length: {}'.format(length)
print ''
with open(outputName, 'rb') as f:
	shutil.copyfileobj(f, sys.stdout)

close_files([pdf, outputName])
