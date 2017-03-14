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
import json
import os

from buildtools import os_utils
from buildtools.bt_logging import log


class BuildTarget(object):
    BT_TYPE = '-'

    def __init__(self, target=None, files=[], dependencies=[]):
        self.target = target
        self.files = files
        self.dependencies = dependencies

        self.maestro = None

    def build(self):
        pass

    def serialize(self):
        return {
            'type': self.BT_TYPE,
            'files': self.files,
            'dependencies': self.dependencies
        }

    def deserialize(self, data):
        self.target = data['target']
        self.files = data.get('files',[])
        self.dependencies = data.get('dependencies',[])

    def checkMTimes(self, inputs, target, config=None):
        if not os.path.isfile(target):
            log.info('%s does not exist.', target)
            return True

        if config is not None:
            configHash = hashlib.sha256(json.dumps(config).encode('utf-8')).hexdigest()
            targetHash = hashlib.sha256(target.encode('utf-8')).hexdigest()

            def writeHash():
                with open(configcachefile, 'w') as f:
                    f.write(configHash)
            os_utils.ensureDirExists('.build')
            configcachefile = os.path.join('.build', targetHash)
            if not os.path.isfile(configcachefile):
                writeHash()
                log.info('%s: Target cache doesn\'t exist.', target)
                return True
            oldConfigHash = ''
            with open(configcachefile, 'r') as f:
                oldConfigHash = f.readline().strip()
            if(oldConfigHash != configHash):
                writeHash()
                log.info('%s: Target config changed.', target)
                return True
        target_mtime = os.stat(target).st_mtime  # must be higher
        for infilename in inputs:
            if os.path.isfile(infilename):
                input_mtime = os.stat(infilename).st_mtime
                # log.info("%d",input_mtime-target_mtime)
                if input_mtime - target_mtime > 1:
                    log.info("%s is newer than %s by %ds!", infilename, target, input_mtime - target_mtime)
                    return True
        return False

    def canBuild(self, maestro):
        for dep in self.dependencies:
            if dep not in maestro.targetsCompleted:
                return False
        return True
