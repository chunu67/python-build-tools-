import codecs
import os
import re
import shutil
import tqdm

from buildtools import log, os_utils, utils
from buildtools.maestro.base_target import SingleBuildTarget
from buildtools.maestro.utils import callLambda


class CopyFileTarget(SingleBuildTarget):
    BT_TYPE = 'CopyFile'
    BT_LABEL = 'COPY'

    def __init__(self, target=None, filename=None, dependencies=[], verbose=False):
        super(CopyFileTarget, self).__init__(target, [filename], dependencies)
        self.name = f'{filename} -> {target}'

    def build(self):
        os_utils.single_copy(self.files[0], self.target, verbose=False)


class MoveFileTarget(SingleBuildTarget):
    BT_TYPE = 'MoveFile'
    BT_LABEL = 'MOVE'

    def __init__(self, target=None, filename=None, dependencies=[]):
        super(MoveFileTarget, self).__init__(target, [filename], dependencies)
        self.name = f'{filename} -> {target}'

    def build(self):
        shutil.move(self.files[0], self.target)


class ReplaceTextTarget(SingleBuildTarget):
    BT_TYPE = 'ReplaceText'
    BT_LABEL = 'REPLACETEXT'

    def __init__(self, target=None, filename=None, replacements=None, dependencies=[], read_encoding='utf-8-sig', write_encoding='utf-8-sig', display_progress=False):
        self.replacements = replacements
        self.subject = filename
        self.read_encoding = read_encoding
        self.write_encoding = write_encoding
        self.display_progress = display_progress
        super(ReplaceTextTarget, self).__init__(target, [filename], dependencies)

    def serialize(self):
        dat = super(ReplaceTextTarget, self).serialize()
        dat['replacements'] = self.replacements
        dat['read-encoding'] = self.read_encoding
        dat['write-encoding'] = self.write_encoding
        if self.display_progress:
            dat['display-progress'] = self.display_progress
        return dat

    def deserialize(self, data):
        super(ReplaceTextTarget, self).deserialize(data)
        self.replacements = data['replacements']
        self.read_encoding = data['read-encoding']
        self.write_encoding = data['write-encoding']
        self.display_progress = data.get('display-progress', False)
        self.subject = data['files'][0]

    def get_config(self):
        return {
            'replacements': self.replacements,
            'read-encoding': self.read_encoding,
            'write-encoding': self.write_encoding
        }

    def build(self):
        def process_line(outf, line):
            for needle, replacement in self.replacements.items():
                needle = callLambda(needle)
                # if isinstance(replacement, SerializableLambda):
                #    replacement = replacement()
                line = re.sub(needle, replacement, line)
            outf.write(line)
        os_utils.ensureDirExists(os.path.dirname(self.target))
        nbytes = os.path.getsize(self.subject)
        with codecs.open(self.subject, 'r', encoding=self.read_encoding) as inf:
            with codecs.open(self.target + '.out', 'w', encoding=self.write_encoding) as outf:
                progBar = tqdm.tqdm(total=nbytes, unit='B', leave=False) if self.display_progress else None
                linebuf = ''
                nlines = 0
                nbytes = 0
                lastbytecount = 0
                lastcheck = 0
                longest_line = 0
                while True:
                    block = inf.read(4096)
                    block = block.replace('\r\n', '\n')
                    block = block.replace('\r', '\n')
                    if not block:  # EOF
                        process_line(outf, linebuf)
                        nlines += 1
                        charsInLine = len(linebuf)
                        if charsInLine > longest_line:
                            longest_line = charsInLine
                        break
                    for c in block:
                        nbytes += 1
                        if self.display_progress:
                            # if nbytes % 10 == 1:
                            cms = utils.current_milli_time()
                            if cms - lastcheck >= 250:
                                progBar.set_postfix({'linebuf': len(linebuf), 'nlines': nlines})
                                progBar.update(nbytes - lastbytecount)
                                lastcheck = cms
                                lastbytecount = nbytes
                        linebuf += c
                        if c in '\r\n':
                            process_line(outf, linebuf)
                            nlines += 1
                            charsInLine = len(linebuf)
                            if charsInLine > longest_line:
                                longest_line = charsInLine
                            linebuf = ''
                if self.display_progress:
                    progBar.close()
                    with log.info('Completed.'):
                        log.info('Lines.......: %d', nlines)
                        log.info('Chars.......: %d', nbytes)
                        log.info('Longest line: %d chars', longest_line)
        shutil.move(self.target + '.out', self.target)


class ConcatenateBuildTarget(SingleBuildTarget):
    BT_TYPE = 'Concatenate'
    BT_LABEL = 'CONCAT'

    def __init__(self, target, files, dependencies=[], read_encoding='utf-8-sig', write_encoding='utf-8-sig'):
        self.write_encoding = write_encoding
        self.read_encoding = read_encoding
        self.subjects = files
        super(ConcatenateBuildTarget, self).__init__(target, dependencies=dependencies, files=[os.path.abspath(__file__)] + files)

    def serialize(self):
        data = super(ConcatenateBuildTarget, self).serialize()
        if os.path.abspath(__file__) in data['files']:
            data['files'].remove(os.path.abspath(__file__))
        data['encoding'] = {
            'read': self.read_encoding,
            'write': self.write_encoding
        }
        return data

    def deserialize(self, data):
        super(ConcatenateBuildTarget, self).deserialize(data)
        if os.path.abspath(__file__) not in data['files']:
            data['files'].append(os.path.abspath(__file__))
        enc = data.get('encoding', {})
        self.read_encoding = enc.get('read', 'utf-8-sig')
        self.write_encoding = enc.get('write', 'utf-8-sig')

    def get_config(self):
        return {
            'read-encoding': self.read_encoding,
            'write-encoding': self.write_encoding
        }

    def build(self):
        with codecs.open(self.target + '.tmp', 'w', encoding=self.write_encoding) as outf:
            for subj in tqdm.tqdm(self.subjects, leave=False):
                with codecs.open(subj, 'r', encoding=self.read_encoding) as f:
                    outf.write(f.read())
        shutil.move(self.target + '.tmp', self.target)


class CopyFilesTarget(SingleBuildTarget):
    BT_TYPE = 'CopyFiles'
    BT_LABEL = 'COPYFILES'

    def __init__(self, target, source, destination, dependencies=[], verbose=True):
        self.source = source
        self.destination = destination
        self.verbose = verbose
        super(CopyFilesTarget, self).__init__(target, dependencies=dependencies, files=[self.source, self.destination, os.path.abspath(__file__)])

    def serialize(self):
        data = super(CopyFilesTarget, self).serialize()
        data['files'] = [self.source, self.destination]
        return data

    def deserialize(self, data):
        super(CopyFilesTarget, self).deserialize(data)
        self.source, self.destination = data['files']

    def getLatestMTimeIn(self, dirpath):
        latest = 0
        for root, _, filenames in os.walk(dirpath):
            for basefilename in filenames:
                filename = os.path.join(root, basefilename)
                current = os.stat(filename).st_mtime
                if latest > current:
                    latest = current
        return latest

    def touch(self, filename):
        os_utils.ensureDirExists(os.path.dirname(filename))
        with open(filename, 'w') as f:
            f.write('a')

    def get_config(self):
        return [self.source, self.destination]

    def is_stale(self):
        return not os.path.isdir(self.destination) or self.getLatestMTimeIn(self.source) > self.getLatestMTimeIn(self.destination) or self.checkMTimes([os.path.abspath(__file__)], [self.target], [self.destination])

    def build(self):
        os_utils.copytree(self.source, self.destination, verbose=self.verbose)
        self.touch(self.target)
