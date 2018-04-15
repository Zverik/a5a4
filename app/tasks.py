import os
import re
import subprocess
import tempfile
import random
import string
from app import app

FILENAME = 'task'
RESULT = 'a5a4.pdf'


class Task:
    def __init__(self):
        self.pages = []  # list of transformations: 'A1', 'B2L' etc.
        self.files = {}  # dict of 'A': TaskFile()


class TaskFile:
    def __init__(self, pages, name):
        self.name = name
        if type(pages) is str:
            self.orient = [p == 'l' for p in pages]
        elif type(pages) is list:
            self.orient = pages
        elif type(pages) is int:
            self.orient = [False for p in xrange(pages)]
        else:
            raise Exception('Incorrect pages value: {}'.format(pages))
        self.pages = len(self.orient)

    def orient_str(self):
        """Produces a string out of orient array."""
        return reduce(lambda a, b: a + ('l' if b else 'p'), self.orient, '')


def taskfile(taskid, name=''):
    """Get absolute file name for a file inside a task folder."""
    if not app.config.get('A5A4_TASKS'):
        folder = os.path.join(app.config['BASE_DIR'], 'tasks')
    else:
        folder = app.config['A5A4_TASKS']
    if not re.match('^[a-z]{3,9}$', taskid):
        raise Exception('Task id is wrong: ' + taskid)
    if not re.match('^[a-zA-Z0-9_%.-]{0,20}$', name):
        raise Exception('File name in task is wrong: ' + name)
    return os.path.join(folder, taskid, name)


def create():
    """Create new task with random id, initialize its task file."""
    found = False
    while not found:
        taskid = ''.join(random.choice(string.lowercase) for i in xrange(3))
        found = not os.path.isfile(taskfile(taskid, FILENAME))
    os.makedirs(taskfile(taskid))
    store(taskid, Task())
    return taskid


def get(taskid):
    """Read and parse task file for a given id. Returns Task object."""
    filename = taskfile(taskid, FILENAME)
    if not os.path.isfile(filename):
        return None
    task = Task()
    with open(filename, 'r') as f:
        task.pages = [p for p in f.readline().strip().split(' ') if len(p)]
        for pdf in f.readlines():
            data = pdf.strip().split(',', 2)
            if len(data) == 3 and len(data[0]) == 1:
                task.files[data[0]] = TaskFile(data[1], data[2])
    return task


def store(taskid, newtask):
    """Stores a Task object into a task folder for given id."""
    with open(taskfile(taskid, FILENAME), 'w') as f:
        f.write(' '.join(newtask.pages) + '\n')
        for k, pdf in newtask.files.items():
            f.write(','.join([k, pdf.orient_str(), pdf.name]) + '\n')


def store_pages(taskid, pages):
    """Stores new page order for a given task. Pages is a list."""
    task = get(taskid)
    if task is None:
        return
    for page in pages:
        if not page[0] in task.files:
            raise Exception(page[0] + ' is not in PDF list')
        if int(page[1]) < 1 or int(page[1]) > task.files[page[0]].pages:
            raise Exception(page[0] + ' does not have page ' + page[1])
        if len(page) > 2 and page[2] not in ['L', 'R', 'D']:
            raise Exception('Unknown rotation mode: ' + page)
    task.pages = pages
    store(taskid, task)


def restore_pages(taskid, pdf):
    """Restores deleted pages at proper places. Pdf is a single-letter identifier."""
    task = get(taskid)
    if task and pdf in task.files and task.files[pdf].pages > 0:
        torestore = range(1, task.files[pdf].pages + 1)
        for p in task.pages:
            if p[0] == pdf:
                try:
                    torestore.remove(int(p[1]))
                except:
                    pass
        insert_rest_before = 0
        foundmax = False
        pos = 0
        while len(torestore) > 0 and pos < len(task.pages):
            if task.pages[pos][0] == pdf:
                curpg = int(task.pages[pos][1])
                while len(torestore) > 0 and curpg > torestore[0]:
                    nextpg = torestore.pop(0)
                    page = '{}{}{}'.format(
                        pdf, nextpg, 'L' if task.files[pdf].orient[nextpg-1] else '')
                    task.pages.insert(pos, page)
                    pos = pos + 1
                insert_rest_before = pos + 1
            elif not insert_rest_before and task.pages[pos][0] > pdf:
                insert_rest_before = pos
                foundmax = True
            pos = pos + 1
        if not foundmax and insert_rest_before == 0:
            insert_rest_before = len(task.pages)
        while len(torestore) > 0:
            nextpg = torestore.pop(0)
            page = '{}{}{}'.format(pdf, nextpg, 'L' if task.files[pdf].orient[nextpg-1] else '')
            task.pages.insert(insert_rest_before, page)
            insert_rest_before = insert_rest_before + 1
        store_pages(taskid, task.pages)


def addpdf(taskid, pdf):
    """Uploads a pdf / png file, converting it and stuff.
    Pdf is a flask uploaded file.
    Return error string or None if it's ok."""
    task = get(taskid)
    if not task or len(task.files) >= app.config['A5A4_MAXFILES']:
        return 'You can have no more than {} files'.format(app.config['A5A4_MAXFILES'])
    if not len(task.files):
        letter = 'A'
    else:
        letter = chr(ord(sorted(task.files.keys(), reverse=True)[0]) + 1)
        if letter > 'Z':
            letter = 'A'
            # this won't overflow because of maxfiles (which should be less than 26)
            while letter in task.files.keys():
                letter = chr(ord(letter) + 1)
    filename = taskfile(taskid, letter + '.pdf')
    pdf.save(filename)

    # check that all pages are A5
    command = [app.config['IDENTIFY'], filename]
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    out, _ = process.communicate()
    code = process.returncode
    if code != 0 or not out:
        os.remove(filename)
        return 'Identify failed: {}'.format(code)

    # check page dimensions
    # get page rotation
    # get number of pages
    pages = []
    for line in out.split('\n'):
        app.logger.debug('Processing {}'.format(line))
        m = re.search(filename + r'(?:\[\d+\])? ([A-Z]{3,4}) (\d+)x(\d+)', line)
        if m:
            fmt = m.group(1)
            width = int(m.group(2))
            height = int(m.group(3))
            landscape = width > height
            if landscape:
                width, height = height, width
            png = fmt != 'PDF'
            if not png and (abs(width - 420) > 4 or abs(height - 595) > 4):
                os.remove(filename)
                return 'Provided PDF is not in A5 format'
            pages.append(landscape)

    if len(pages) == 0:
        os.remove(filename)
        return 'No pages parsed from identify'

    if reduce(lambda c, t: c + t.pages,
              task.files.values(), len(pages)) > app.config['A5A4_MAXPAGES']:
        os.remove(filename)
        return 'Too many pages: {} (maximum is {})'.format(len(pages), app.config['A5A4_MAXPAGES'])

    # check if source is png
    if png:
        app.logger.debug('converting to png')
        # convert to pdf
        tmpfile, tmpName = tempfile.mkstemp(suffix='.pdf')
        command = [app.config['CONVERT'], filename, '-bordercolor', 'white',
                   '-border', '6%', '-rotate', '-90>', tmpName]
        result = subprocess.call(command)
        os.remove(filename)
        if result != 0:
            return 'Convert to PNG failed: {}'.format(result)
        pages = [False for i in pages]
        # resize pdf to A5
        command = [app.config['PDFJAM'], '--a5paper', '--no-landscape',
                   '--outfile', filename, tmpName]
        result = subprocess.call(command)
        os.remove(tmpName)
        if result != 0:
            os.remove(filename)
            return 'Scaling PNG pdf with pdfjam failed: {}'.format(result)

    # generate slides
    command = [app.config['CONVERT'], '-density', '200', filename,
               '-alpha', 'opaque', '-resize', '200x200^',
               taskfile(taskid, letter + '%d.png')]
    result = subprocess.call(command)
    if result != 0:
        os.remove(filename)
        return 'Creating png pages from pdf failed: {}'.format(result)

    # rotate landscape images
    for i in xrange(len(pages)):
        task.pages.append('{}{}{}'.format(letter, i+1, 'L' if pages[i] else ''))
        if pages[i]:
            pagename = taskfile(taskid, letter + str(i) + '.png')
            command = [app.config['CONVERT'], pagename, '-rotate', '-90', pagename]
            result = subprocess.call(command)
            if result != 0:
                app.logger.warn('Failed to rotate image {}'.format(pagename))

    # construct TaskFile object and store it
    task.files[letter] = TaskFile(pages, pdf.filename)
    store(taskid, task)
    return None


def delpdf(taskid, idx):
    """Deletes a PDF file, all png miniatures and all of its pages."""
    task = get(taskid)
    if not task or not len(idx) == 1 or idx not in task.files:
        return False
    pdf = task.files[idx]
    # delete pdf
    try:
        os.remove(taskfile(taskid, '{}.pdf'.format(idx)))
    except OSError:
        app.logger.warn('Failed to delete {}/{}'.format(taskid, pdf.name))
    # delete pngs
    for i in xrange(pdf.pages):
        try:
            os.remove(taskfile(taskid, '{}{}.png'.format(idx, i)))
        except OSError:
            app.logger.warn('Failed to delete {}/{}{}.png'.format(taskid, idx, i))
    # update tasks file
    task.pages = [p for p in task.pages if not p.startswith(idx)]
    del task.files[idx]
    store(taskid, task)
    return True


def generate(taskid):
    """Creates a resulting PDF for a task with pdftk and pdfjam."""
    task = get(taskid)
    if not task or not len(task.pages) or not len(task.files):
        return False
    rotation = {'W': 'west', 'E': 'east', 'S': 'south',
                'L': 'left', 'R': 'right',
                'D': 'down', 'N': 'north'}
    if app.config['PDFTK_NEW']:
        def fix_rot(page):
            for k, v in rotation.items():
                if len(page) >= 3 and page.endswith(k):
                    return page[:-1] + v
            return page
        task.pages = [fix_rot(p) for p in task.pages]

    tmpfile, tmpName = tempfile.mkstemp(suffix='.pdf')
    command = [app.config['PDFTK']]
    # this line leaves only those documents mentioned in pages
    command.extend(['{}={}'.format(k, taskfile(taskid, '{}.pdf'.format(k)))
                    for k in set([page[0:1] for page in task.pages])
                    if k in task.files])
    command.append('cat')
    command.extend(task.pages)
    command.extend(['output', tmpName])
    process = subprocess.Popen(command, stderr=subprocess.PIPE)
    _, err = process.communicate()
    result = process.returncode
    if result != 0 or not os.path.isfile(tmpName) or os.stat(tmpName).st_size == 0:
        app.logger.error('PDFtk returned error code {}\n\n{}'.format(result, err))
    else:
        # now process result with pdfjam
        command = [app.config['PDFJAM'], tmpName,
                   '--nup', '2x1', '--landscape', '--a4paper', '--outfile',
                   taskfile(taskid, RESULT)]
        process = subprocess.Popen(command, stderr=subprocess.PIPE)
        _, err = process.communicate()
        result = process.returncode
        if result != 0:
            app.logger.error('PDFjam returned error code {}\n\n{}'.format(result, err))

    try:
        os.remove(tmpName)
    except OSError:
        pass
    return result == 0
