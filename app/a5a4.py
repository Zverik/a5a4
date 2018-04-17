#!/usr/bin/python
from app import app
import re
from flask import render_template, send_file, request, session, url_for, redirect
import app.tasks as tasks


@app.route('/')
def index():
    if 'logged_in' in session and session['logged_in']:
        return render_template('upload.html')
    else:
        return render_template('login.html')


@app.route('/login', methods=['POST'])
def login():
    if 'A5A4_PASSWORD' not in app.config or request.form['password'] == app.config['A5A4_PASSWORD']:
        session['logged_in'] = True
        if len(request.form['taskid']) > 1:
            return redirect(url_for('task', taskid=request.form['taskid']))
    return redirect(url_for('index'))


@app.route('/<taskid>')
def task(taskid, error=None):
    if 'logged_in' not in session or not session['logged_in']:
        return render_template('login.html', taskid=taskid)
    task = tasks.get(taskid)
    if not task:
        return redirect(url_for('index'))
    return render_template('task.html', taskid=taskid, pages=task.pages,
                           files=task.files, error=error)


@app.route('/<taskid>/update')
def task_update(taskid):
    pages = request.args.get('pages', '-')
    try:
        if pages != '-':
            tasks.store_pages(taskid, re.split(r'\s+', pages.strip()))
        return 'ok'
    except Exception as e:
        app.logger.error('Error saving pages {}: {}'.format(pages, e))
        return 'fail'


@app.route('/<taskid>/upload', methods=['POST'])
@app.route('/upload', methods=['POST'])
def upload(taskid=None):
    if 'logged_in' not in session or not session['logged_in']:
        return render_template('login.html')
    pdf = request.files['pdf']
    if not pdf:
        return render_template('upload.html')
    newtask = not taskid
    if not taskid:
        taskid = tasks.create()
    result = tasks.addpdf(taskid, pdf)
    if result and newtask:
        return render_template('upload.html', error=result)
    return redirect(url_for('task', taskid=taskid, error=result))


@app.route('/<taskid>/<img>.png')
def getpng(taskid, img):
    m = re.match('^([A-Z])(\d+)[LRD]?$', img)
    if not m:
        return
    return send_file(tasks.taskfile(taskid, m.group(1) + str(int(m.group(2))-1) + '.png'))


@app.route('/<taskid>/delete/<name>')
def delpdf(taskid, name):
    if 'logged_in' not in session or not session['logged_in']:
        return render_template('login.html')
    tasks.delpdf(taskid, name)
    return redirect(url_for('task', taskid=taskid))


@app.route('/<taskid>/result')
def getresult(taskid):
    return send_file(tasks.taskfile(taskid, tasks.RESULT))


@app.route('/<taskid>/generate')
def generate(taskid):
    if 'logged_in' not in session or not session['logged_in']:
        return render_template('login.html')
    result = tasks.generate(taskid)
    if result:
        return send_file(
            tasks.taskfile(taskid, tasks.RESULT),
            as_attachment=True,
            mimetype='application/pdf',
            attachment_filename='a5a4_result.pdf')
    else:
        return redirect(url_for('task', taskid=taskid))


@app.route('/<taskid>/restorepg/<name>')
def restorepg(taskid, name):
    tasks.restore_pages(taskid, name)
    return redirect(url_for('task', taskid=taskid))
