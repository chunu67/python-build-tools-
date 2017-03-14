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
import os
from buildtools.maestro.base_target import BuildTarget
from buildtools import os_utils, log
class SCSSBuildTarget(BuildTarget):
    BT_TYPE = 'SCSS'

    def __init__(self, target=None, files=[], dependencies=[], compass=False, import_paths=[]):
        super(SCSSBuildTarget, self).__init__(target, files, dependencies)
        self.compass = compass
        self.import_paths = import_paths

    def serialize(self):
        dat= super(SCSSBuildTarget,self).serialize()
        dat['compass']=self.compass
        dat['imports']=self.import_paths
        return dat

    def deserialize(self,data):
        super(SCSSBuildTarget,self).deserialize(data)
        self.compass=data.get('compass',False)
        self.import_paths=data.get('imports',[])

    def build(self):
        sass_cmd = []
        if SASS.endswith('.bat') or SASS.endswith('.BAT'):
            RUBYDIR = os.path.dirname(SASS)
            sass_cmd = [os.path.join(RUBYDIR, 'ruby.exe'), os.path.join(RUBYDIR, 'sass')]
        else:
            sass_cmd = [SASS]
        args = ['--scss', '--force', '-C', '-t', 'compact']
        if self.compass:
            args += ['--compass']
        for import_path in self.import_paths:
            args += ['-I=' + import_path]
        if self.checkMTimes(self.files, self.target, config=args):
            os_utils.ensureDirExists(os.path.join('tmp', os.path.dirname(self.target)))
            os_utils.ensureDirExists(os.path.dirname(self.target))
            #log.info("SASS %s", self.target)
            os_utils.cmd(sass_cmd + args + self.files + [self.target], critical=True, echo=True, show_output=True)


class SCSSConvertTarget(BuildTarget):
    BT_TYPE = 'SCSSConvert'

    def __init__(self, target=None, files=[], dependencies=[]):
        super(SCSSConvertTarget, self).__init__(target, files, dependencies)

    def build(self):
        sass_cmd = []
        if SASS_CONVERT.endswith('.bat') or SASS_CONVERT.endswith('.BAT'):
            RUBYDIR = os.path.dirname(SASS_CONVERT)
            sass_cmd = [os.path.join(RUBYDIR, 'ruby.exe'), os.path.join(RUBYDIR, 'sass-convert')]
        else:
            sass_cmd = [SASS_CONVERT]
        args = ['-F','css','-T','scss','-C']
        if self.checkMTimes(self.files, self.target, config=args):
            os_utils.ensureDirExists(os.path.join('tmp', os.path.dirname(self.target)))
            os_utils.ensureDirExists(os.path.dirname(self.target))
            #log.info("SASS %s", self.target)
            os_utils.cmd(sass_cmd + args + self.files + [self.target], critical=True, echo=True, show_output=True)


SASS = os_utils.which('sass')
if SASS is None:
    log.warn('Unable to find sass on this OS.  Is it in PATH?  Remember to run `gem install sass compass`!')

SASS_CONVERT = os_utils.which('sass-convert')
if SASS_CONVERT is None:
    log.warn('Unable to find sass-convert on this OS.  Is it in PATH?  Remember to run `gem install sass compass`!')
