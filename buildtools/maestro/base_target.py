'''
BLURB GOES HERE.

Copyright (c) 2015 - 2017 Rob "N3X15" Nelson <nexisentertainment@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

'''
import hashlib
import yaml
import os

from pathlib import Path

from buildtools import os_utils
from buildtools.bt_logging import log
from buildtools.maestro.utils import callLambda


class BuildTarget(object):
    BT_TYPE = '-'
    BT_COLOR = 'cyan'
    BT_LABEL = None

    def __init__(self, targets=None, files=[], dependencies=[], provides=[], name=''):
        self._all_provides = targets if isinstance(targets, list) else [targets]+provides
        self.name = ''
        try:
            self.name = os.path.relpath(self._all_provides[0], os.getcwd()) if name == '' else name
        except ValueError:
            self.name = self._all_provides[0] if name == '' else name
        self.files = files
        self.dependencies = dependencies

        self.maestro = None

        #: This target was rebuilt. (Files changed)
        self.dirty = False

        self._lambdas_called=False

    def try_build(self):
        self.files = callLambda(self.files)
        if self.is_stale():
            with self.logStart():
                self.build()

    def get_config(self):
        return {}

    def is_stale(self):
        return self.checkMTimes(self.files+self.dependencies, self.provides(), config=self.get_config())

    def build(self):
        pass

    def provides(self):
        return self._all_provides

    def get_label(self):
        return self.BT_LABEL or self.BT_TYPE.upper() or type(self).__class__.__name__

    def verboseLogEntry(self, color):
        if self.maestro.colors:
            return f'Running target <{color}>{self.name}</{color}>...'
        else:
            return f'Running target {self.name}...'

    def standardLogEntry(self, color):
        padded_label = self.get_label().ljust(self.maestro.get_max_label_length())
        if self.maestro.colors:
            return f'<{color}>{padded_label}</{color}> {self.name}'
        else:
            return f'{padded_label} {self.name}'

    def logStart(self):
        color = self.BT_COLOR or 'cyan'
        pct = round((len(self.maestro.targetsCompleted)/len(self.maestro.targets))*100)
        msg = ''
        if self.maestro.verbose:
            msg = self.verboseLogEntry(color)
        else:
            msg = self.standardLogEntry(color)
        return log.info(f'[{str(pct).rjust(3)}%] {msg}')

    def serialize(self):
        return {
            'type': self.BT_TYPE,
            'name': self.name,
            'files': callLambda(self.files),
            'dependencies': self.dependencies,
            'provides': self.provides()
        }

    def genVirtualTarget(self, vid=None):
        if vid is None:
            vid = self.name
        return os.path.join('.build', 'tmp', 'virtual-targets', vid)

    def deserialize(self, data):
        self.target = data['target']
        self.files = data.get('files', [])
        self.dependencies = data.get('dependencies', [])
        self._all_provides = data.get('provides', [])

    def checkMTimes(self, inputs, targets, config=None):
        inputs=callLambda(inputs)
        for target in targets:
            if not os.path.isfile(target):
                log.debug('%s does not exist.', target)
                return True

        if config is not None:
            configHash = hashlib.sha256(yaml.dump(config).encode('utf-8')).hexdigest()
            targetHash = hashlib.sha256(';'.join(targets).encode('utf-8')).hexdigest()

            def writeHash():
                with open(configcachefile, 'w') as f:
                    f.write(configHash)
            os_utils.ensureDirExists('.build')
            configcachefile = os.path.join('.build', targetHash)
            if not os.path.isfile(configcachefile):
                writeHash()
                log.debug('%s: Target cache doesn\'t exist.', self.name)
                return True
            oldConfigHash = ''
            with open(configcachefile, 'r') as f:
                oldConfigHash = f.readline().strip()
            if(oldConfigHash != configHash):
                writeHash()
                log.debug('%s: Target config changed.', self.name)
                return True
        target_mtime = 0  # must be higher
        newest_target = None
        inputs_mtime = 0
        newest_input = None
        for infilename in targets:
            infilename = callLambda(infilename)
            if os.path.isfile(infilename):
                c_mtime = os.stat(infilename).st_mtime
                # log.info("%d",input_mtime-target_mtime)
                if c_mtime > target_mtime:
                    target_mtime = c_mtime
                    newest_target = infilename
        for infilename in inputs:
            infilename = callLambda(infilename)
            if os.path.isfile(infilename):
                c_mtime = os.stat(infilename).st_mtime
                # log.info("%d",input_mtime-target_mtime)
                if c_mtime > inputs_mtime:
                    inputs_mtime = c_mtime
                    newest_input = infilename
        if newest_input is None or target_mtime <= inputs_mtime:
            log.debug("%s is newer than %s by %ds!", newest_input, newest_target, inputs_mtime - target_mtime)
            return True
        else:
            log.debug("%s is older than %s by %ds!", newest_input, newest_target, target_mtime - inputs_mtime)

        return False

    def canBuild(self, maestro, keys):
        #self.files = list(callLambda(self.files))
        #for dep in list(set(self.dependencies + self.files)):
        if not self._lambdas_called:
            for reqfile in callLambda(self.files):
                if reqfile in keys and reqfile not in self.dependencies:
                    self.dependencies.append(reqfile)
        for dep in list(set(self.dependencies)):
            if dep not in maestro.targetsCompleted:
                log.debug('%s: Waiting on %s.',self.name,dep)
                return False
        return True

    def touch(self, filename):
        os_utils.ensureDirExists(os.path.dirname(filename))
        Path(filename).touch(exist_ok=True)

class SingleBuildTarget(BuildTarget):
    def __init__(self, target=None, files=[], dependencies=[], provides=[], name=''):
        self.target=target
        super(SingleBuildTarget, self).__init__([target], files=files, dependencies=dependencies, provides=provides, name=name)
